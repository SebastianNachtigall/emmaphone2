"""
EmmaPhone2 Pi Web Interface Server

Local web server for Pi setup, monitoring, and management
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_socketio import SocketIO, emit
import threading
import time

from config.settings import Settings
from services.user_manager import UserManager

logger = logging.getLogger(__name__)

class PiWebServer:
    """Flask web server for Pi management interface"""
    
    def __init__(self, settings: Settings, port: int = 8080):
        self.settings = settings
        self.port = port
        self.app = Flask(__name__, 
                        template_folder=str(Path(__file__).parent / "templates"),
                        static_folder=str(Path(__file__).parent / "static"))
        
        self.app.secret_key = "emmaphone2-pi-web-interface"
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Application state
        self.call_manager = None
        self.user_manager = None
        self.audio_manager = None
        self.led_controller = None
        self.main_event_loop = None  # Reference to main event loop
        self.system_status = {
            "wifi_connected": False,
            "user_configured": False,
            "call_state": "idle",
            "audio_devices": [],
            "last_update": None
        }
        
        self.setup_routes()
        self.setup_socketio_events()
        
    def set_managers(self, call_manager=None, user_manager=None, audio_manager=None, led_controller=None):
        """Set manager instances for status monitoring"""
        self.call_manager = call_manager
        self.user_manager = user_manager
        self.audio_manager = audio_manager
        self.led_controller = led_controller
        
        # Store reference to the current event loop
        try:
            self.main_event_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop running, will handle this in the API calls
            self.main_event_loop = None
        
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main dashboard"""
            return render_template('index.html', 
                                 settings=self.settings,
                                 status=self.system_status)
        
        @self.app.route('/setup')
        def setup():
            """User setup page"""
            return render_template('setup.html', 
                                 settings=self.settings,
                                 user_configured=self.settings.is_user_configured())
        
        @self.app.route('/setup/user', methods=['POST'])
        def setup_user():
            """Handle user setup form"""
            try:
                username = request.form.get('username', '').strip()
                display_name = request.form.get('display_name', '').strip()
                password = request.form.get('password', '')
                
                if not all([username, display_name, password]):
                    flash('All fields are required', 'error')
                    return redirect(url_for('setup'))
                
                if len(password) < 6:
                    flash('Password must be at least 6 characters', 'error')
                    return redirect(url_for('setup'))
                
                # Configure user in settings
                self.settings.configure_user(username, display_name, password)
                
                flash(f'User {username} configured successfully!', 'success')
                return redirect(url_for('index'))
                
            except Exception as e:
                logger.error(f"Failed to setup user: {e}")
                flash(f'Setup failed: {e}', 'error')
                return redirect(url_for('setup'))
        
        @self.app.route('/contacts')
        def contacts():
            """Speed dial contacts management"""
            contacts = self.settings.get_contacts()
            return render_template('contacts.html', 
                                 contacts=contacts,
                                 settings=self.settings)
        
        @self.app.route('/contacts/add', methods=['POST'])
        def add_contact():
            """Add speed dial contact"""
            try:
                name = request.form.get('name', '').strip()
                user_id = request.form.get('user_id', '').strip()
                position = request.form.get('position', '')
                
                if not all([name, user_id, position]):
                    flash('All fields are required', 'error')
                    return redirect(url_for('contacts'))
                
                position = int(position)
                if position < 1 or position > 4:
                    flash('Position must be between 1 and 4', 'error')
                    return redirect(url_for('contacts'))
                
                # Check if position is already taken
                contacts = self.settings.get_contacts()
                if any(c.get('speed_dial') == position for c in contacts):
                    flash(f'Position {position} is already taken', 'error')
                    return redirect(url_for('contacts'))
                
                self.settings.add_contact(name, user_id, position)
                flash(f'Contact {name} added to position {position}', 'success')
                
            except ValueError:
                flash('Invalid position number', 'error')
            except Exception as e:
                logger.error(f"Failed to add contact: {e}")
                flash(f'Failed to add contact: {e}', 'error')
            
            return redirect(url_for('contacts'))
        
        @self.app.route('/contacts/remove', methods=['POST'])
        def remove_contact():
            """Remove speed dial contact"""
            try:
                contact_name = request.form.get('contact_name', '').strip()
                
                if not contact_name:
                    flash('Contact name is required', 'error')
                    return redirect(url_for('contacts'))
                
                success = self.settings.remove_contact(contact_name=contact_name)
                if success:
                    flash(f'Contact {contact_name} removed', 'success')
                else:
                    flash(f'Contact {contact_name} not found', 'error')
                
            except Exception as e:
                logger.error(f"Failed to remove contact: {e}")
                flash(f'Failed to remove contact: {e}', 'error')
            
            return redirect(url_for('contacts'))
        
        @self.app.route('/status')
        def status():
            """System status page"""
            return render_template('status.html', 
                                 status=self.get_system_status(),
                                 settings=self.settings)
        
        @self.app.route('/api/status')
        def api_status():
            """API endpoint for system status"""
            return jsonify(self.get_system_status())
        
        @self.app.route('/api/audio/test', methods=['POST'])
        def api_audio_test():
            """API endpoint to test audio recording"""
            try:
                if not self.audio_manager:
                    return jsonify({"error": "Audio manager not available"}), 503
                
                # Run audio test in thread-safe way
                import threading
                
                test_result = {"success": False, "error": None}
                
                def run_audio_test():
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        # Test audio recording for 2 seconds
                        audio_data = loop.run_until_complete(
                            self.audio_manager.record_audio(duration=2.0)
                        )
                        
                        if audio_data:
                            test_result["success"] = True
                            test_result["data_length"] = len(audio_data)
                        else:
                            test_result["error"] = "No audio data recorded"
                        
                        loop.close()
                    except Exception as e:
                        test_result["error"] = str(e)
                
                thread = threading.Thread(target=run_audio_test, daemon=True)
                thread.start()
                thread.join(timeout=5)  # Wait max 5 seconds
                
                return jsonify(test_result)
                
            except Exception as e:
                logger.error(f"Failed to test audio: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/audio/level')
        def api_audio_level():
            """API endpoint to get current audio input level"""
            try:
                if not self.audio_manager:
                    return jsonify({"error": "Audio manager not available"}), 503
                
                # This would need to be called from the main event loop
                # For now, return a placeholder
                return jsonify({
                    "level": 0.0,
                    "recording": getattr(self.audio_manager, 'recording', False),
                    "playing": getattr(self.audio_manager, 'playing', False)
                })
                
            except Exception as e:
                logger.error(f"Failed to get audio level: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/call/<user_id>', methods=['POST'])
        def api_call(user_id):
            """API endpoint to initiate call"""
            try:
                if not self.call_manager:
                    return jsonify({"error": "Call manager not available"}), 503
                
                # Run async call in main event loop if available
                if self.main_event_loop:
                    try:
                        # Schedule coroutine in main event loop
                        future = asyncio.run_coroutine_threadsafe(
                            self.call_manager.initiate_call(user_id), 
                            self.main_event_loop
                        )
                        # Don't wait for completion, return immediately
                    except Exception as e:
                        logger.error(f"Failed to schedule call: {e}")
                        return jsonify({"error": f"Failed to schedule call: {e}"}), 500
                else:
                    # Fallback: try to run in new event loop
                    import threading
                    
                    def run_async_call():
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(self.call_manager.initiate_call(user_id))
                            loop.close()
                        except Exception as e:
                            logger.error(f"Async call failed: {e}")
                    
                    thread = threading.Thread(target=run_async_call, daemon=True)
                    thread.start()
                
                return jsonify({"success": True, "message": f"Call initiated to user {user_id}"})
                
            except Exception as e:
                logger.error(f"Failed to initiate call: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/hangup', methods=['POST'])
        def api_hangup():
            """API endpoint to hang up call"""
            try:
                if not self.call_manager:
                    return jsonify({"error": "Call manager not available"}), 503
                
                # Run async hangup in main event loop if available
                if self.main_event_loop:
                    try:
                        # Schedule coroutine in main event loop
                        future = asyncio.run_coroutine_threadsafe(
                            self.call_manager.hang_up(), 
                            self.main_event_loop
                        )
                        # Don't wait for completion, return immediately
                    except Exception as e:
                        logger.error(f"Failed to schedule hangup: {e}")
                        return jsonify({"error": f"Failed to schedule hangup: {e}"}), 500
                else:
                    # Fallback: try to run in new event loop
                    import threading
                    
                    def run_async_hangup():
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(self.call_manager.hang_up())
                            loop.close()
                        except Exception as e:
                            logger.error(f"Async hangup failed: {e}")
                    
                    thread = threading.Thread(target=run_async_hangup, daemon=True)
                    thread.start()
                
                return jsonify({"success": True, "message": "Call hung up"})
                
            except Exception as e:
                logger.error(f"Failed to hang up call: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/config')
        def config():
            """Configuration page"""
            return render_template('config.html', 
                                 settings=self.settings)
        
        @self.app.route('/config/save', methods=['POST'])
        def save_config():
            """Save configuration changes"""
            try:
                # Update web client URL
                web_url = request.form.get('web_url', '').strip()
                if web_url:
                    self.settings.set('web_client.url', web_url)
                
                # Update LiveKit configuration
                livekit_url = request.form.get('livekit_url', '').strip()
                livekit_key = request.form.get('livekit_key', '').strip()
                livekit_secret = request.form.get('livekit_secret', '').strip()
                
                if livekit_url:
                    self.settings.set('livekit.url', livekit_url)
                if livekit_key:
                    self.settings.set('livekit.api_key', livekit_key)
                if livekit_secret:
                    self.settings.set('livekit.api_secret', livekit_secret)
                
                self.settings.save_settings()
                flash('Configuration saved successfully!', 'success')
                
            except Exception as e:
                logger.error(f"Failed to save config: {e}")
                flash(f'Failed to save configuration: {e}', 'error')
            
            return redirect(url_for('config'))
    
    def setup_socketio_events(self):
        """Setup Socket.IO events for real-time updates"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            logger.info("Web client connected")
            emit('status_update', self.get_system_status())
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            logger.info("Web client disconnected")
        
        @self.socketio.on('get_status')
        def handle_get_status():
            """Handle status request"""
            emit('status_update', self.get_system_status())
    
    def get_system_status(self) -> Dict:
        """Get current system status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "wifi_connected": True,  # TODO: Get actual WiFi status
            "user_configured": self.settings.is_user_configured(),
            "call_state": "idle",
            "current_call": None,
            "contacts": self.settings.get_contacts(),
            "audio_devices": [],
            "web_server_running": True
        }
        
        # Get call manager status
        if self.call_manager:
            try:
                status["call_state"] = self.call_manager.get_call_state().value
                current_call = self.call_manager.get_current_call()
                if current_call:
                    status["current_call"] = {
                        "caller_name": current_call.caller_name,
                        "callee_name": current_call.callee_name,
                        "state": current_call.state.value,
                        "start_time": current_call.start_time
                    }
                status["web_client_connected"] = self.call_manager.is_connected_to_web_client()
            except Exception as e:
                logger.error(f"Error getting call manager status: {e}")
        
        # Get audio device status
        if self.audio_manager:
            try:
                # This would be async, so we'll skip for now or handle differently
                pass
            except Exception as e:
                logger.error(f"Error getting audio status: {e}")
        
        # Get user info
        if self.user_manager and self.settings.is_user_configured():
            user_creds = self.settings.get_user_credentials()
            status["user"] = {
                "username": user_creds.get("username", ""),
                "display_name": user_creds.get("display_name", ""),
                "user_id": user_creds.get("user_id", "")
            }
        
        self.system_status = status
        return status
    
    def broadcast_status_update(self):
        """Broadcast status update to all connected clients"""
        try:
            status = self.get_system_status()
            self.socketio.emit('status_update', status)
        except Exception as e:
            logger.error(f"Failed to broadcast status update: {e}")
    
    def run(self, host='0.0.0.0', debug=False):
        """Run the web server"""
        logger.info(f"Starting Pi web interface on http://{host}:{self.port}")
        
        # Start status update thread
        def status_updater():
            while True:
                time.sleep(5)  # Update every 5 seconds
                self.broadcast_status_update()
        
        status_thread = threading.Thread(target=status_updater, daemon=True)
        status_thread.start()
        
        # Run Flask-SocketIO server
        self.socketio.run(self.app, host=host, port=self.port, debug=debug, allow_unsafe_werkzeug=True)
    
    def stop(self):
        """Stop the web server"""
        logger.info("Stopping Pi web interface")
        # Flask-SocketIO doesn't have a clean stop method, we'll rely on process termination