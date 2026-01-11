# src/services/automation_service.py
"""
Automation service - handles scheduled device control
Checks at 12:00 every day if it's a watering day and triggers pump
"""
import threading
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AutomationService:
    """Manages automated device control (watering schedule)"""
    
    def __init__(self, device_manager, control_service, settings_service):
        """
        Initialize automation service
        
        Args:
            device_manager: DeviceManager instance
            control_service: ControlService instance
            settings_service: SettingsService instance
        """
        self.device_manager = device_manager
        self.control_service = control_service
        self.settings_service = settings_service
        
        self.running = False
        self.automation_thread = None
        logger.info("⚙️  Automation service initialized")
        print("✅ AutomationService.__init__() called")
    
    def start(self):
        """Start automation service background thread"""
        if self.running:
            logger.warning("⚠️  Automation service already running")
            return
        
        self.running = True
        self.automation_thread = threading.Thread(target=self._automation_loop, daemon=True)
        self.automation_thread.start()
        logger.info("✅ Automation service started - will check at 12:00 daily")
        print("🚀 AutomationService.start() - background thread launched!")
    
    def stop(self):
        """Stop automation service"""
        self.running = False
        if self.automation_thread:
            self.automation_thread.join(timeout=5)
        logger.info("🛑 Automation service stopped")
    
    def _automation_loop(self):
        """
        Main automation loop
        Sleeps until 12:00, then executes watering check
        Efficient - no polling!
        """
        logger.info("🔄 Automation loop started")
        print("🔄 Automation loop started - waiting for 12:00...")
        
        while self.running:
            try:
                # Calculate seconds until 12:00 today
                seconds_until_noon = self._get_seconds_until_noon()
                
                logger.info(f"⏰ Next watering check in {seconds_until_noon} seconds ({seconds_until_noon/3600:.1f} hours)")
                
                # Sleep until it's time to check (sleep in chunks to be responsive to stop signal)
                remaining = seconds_until_noon
                while remaining > 0 and self.running:
                    sleep_time = min(remaining, 60)  # Sleep max 60 seconds at a time
                    time.sleep(sleep_time)
                    remaining -= sleep_time
                
                # It's 12:00 - check and water
                if self.running:
                    logger.info("🕐 Watering check time!")
                    self._check_and_water()
                
            except Exception as e:
                logger.error(f"❌ Error in automation loop: {e}", exc_info=True)
                # Continue running even if error occurred
                time.sleep(60)
    
    def _get_seconds_until_noon(self) -> int:
        """
        Calculate seconds until 12:00 today or tomorrow
        Returns positive integer (number of seconds)
        """
        now = datetime.now()
        noon_today = now.replace(hour=12, minute=0, second=0, microsecond=0)
        
        if now < noon_today:
            # 12:00 hasn't happened yet today
            delta = noon_today - now
        else:
            # 12:00 already passed today, wait for tomorrow
            noon_tomorrow = noon_today + timedelta(days=1)
            delta = noon_tomorrow - now
        
        return int(delta.total_seconds())
    
    def _check_and_water(self):
        """
        Check if today is a watering day at 12:00
        If yes, trigger watering sequence
        """
        try:
            # Check if in manual mode - skip automation if manual
            if self.settings_service.is_manual_mode():
                logger.info("⏭️  Manual mode active - skipping automation")
                return
            
            # Check if should water (based on watering_days schedule)
            if self.control_service.should_water():
                logger.info("💧 Watering time! Starting pump...")
                self._water_plant()
            else:
                logger.info("📅 Not a watering day today")
                
        except Exception as e:
            logger.error(f"❌ Error checking watering: {e}", exc_info=True)
    
    def _water_plant(self):
        """
        Execute watering sequence:
        1. Turn on pump
        2. Wait for water_seconds duration
        3. Turn off pump
        """
        try:
            # Get watering duration from settings
            water_seconds = self.settings_service.get_setting("water_seconds", 1)
            
            logger.info(f"💧 Turning on pump for {water_seconds} second(s)...")
            self.device_manager.set_pump(True)
            
            # Wait for specified duration
            time.sleep(water_seconds)
            
            # Turn off pump
            logger.info("🛑 Turning off pump")
            self.device_manager.set_pump(False)
            
            logger.info("✅ Watering complete")
            
        except Exception as e:
            logger.error(f"❌ Error during watering: {e}", exc_info=True)
            # Ensure pump is off even if error occurs
            try:
                self.device_manager.set_pump(False)
            except:
                pass
