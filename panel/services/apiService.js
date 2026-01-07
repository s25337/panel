// services/apiService.js
// Usługa do komunikacji z backend'em IoT

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const apiService = {
  /**
   * Pobiera aktualne wartości czujników
   */
  async getSensors() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/sensors`);
      if (!response.ok) throw new Error('Failed to fetch sensors');
      return await response.json();
    } catch (error) {
      console.error('Error fetching sensors:', error);
      return { temperature: null, humidity: null };
    }
  },

  /**
   * Pobiera status wszystkich urządzeń
   */
  async getStatus() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/status`);
      if (!response.ok) throw new Error('Failed to fetch status');
      return await response.json();
    } catch (error) {
      console.error('Error fetching status:', error);
      return { fan: false, light: false, pump: false };
    }
  },

  /**
   * Steruje urządzeniami
   * @param {object} control - { fan?: boolean, light?: boolean, pump?: boolean }
   */
  async controlDevice(control) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(control),
      });
      if (!response.ok) throw new Error('Failed to control device');
      return await response.json();
    } catch (error) {
      console.error('Error controlling device:', error);
      return { status: 'error' };
    }
  },

  /**
   * Steruje konkretnym urządzeniem
   * @param {string} device - 'fan', 'light' lub 'pump'
   * @param {string} state - 'on' lub 'off'
   */
  async toggleDevice(device, state) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/control/${device}/${state}`,
        { method: 'POST' }
      );
      if (!response.ok) throw new Error(`Failed to toggle ${device}`);
      return await response.json();
    } catch (error) {
      console.error(`Error toggling ${device}:`, error);
      return { status: 'error' };
    }
  },

  /**
   * Pobiera aktualne ustawienia docelowe
   */
  async getSettings() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/settings`);
      if (!response.ok) throw new Error('Failed to fetch settings');
      return await response.json();
    } catch (error) {
      console.error('Error fetching settings:', error);
      return { target_temp: 25, target_hum: 60 };
    }
  },

  /**
   * Aktualizuje ustawienia docelowe
   * @param {object} settings - { target_temp?: number, target_hum?: number }
   */
  async updateSettings(settings) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (!response.ok) throw new Error('Failed to update settings');
      return await response.json();
    } catch (error) {
      console.error('Error updating settings:', error);
      return { status: 'error' };
    }
  },

  /**
   * Pobiera czas do następnego podlewania
   */
  async getWateringTimer() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/watering-timer`);
      if (!response.ok) throw new Error('Failed to fetch watering timer');
      return await response.json();
    } catch (error) {
      console.error('Error fetching watering timer:', error);
      return { 
        days: 2, 
        hours: 10, 
        minutes: 0, 
        seconds: 0,
        interval_seconds: 0
      };
    }
  },

  /**
   * Pobiera harmonogram światła
   */
  async getLightSchedule() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/light-schedule`);
      if (!response.ok) throw new Error('Failed to fetch light schedule');
      return await response.json();
    } catch (error) {
      console.error('Error fetching light schedule:', error);
      return { 
        light_hours: 12,
        start_hour: 6,
        start_minute: 0,
        end_hour: 18,
        end_minute: 0
      };
    }
  },
};

export default apiService;