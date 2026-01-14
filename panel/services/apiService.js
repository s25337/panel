
  /**
   * Wywołuje podlewanie (uruchamia pompę na water_seconds)
   */

// services/apiService.js
// Usługa do komunikacji z backend'em IoT

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Helper function to fetch with timeout
const fetchWithTimeout = async (url, options = {}, timeout = 5000) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
};

const apiService = {
    /**
     * Uruchamia BluetoothService na backendzie
     */
    async startBluetooth() {
      try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/api/bluetooth/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
        if (!response.ok) throw new Error('Failed to start bluetooth');
        return await response.json();
      } catch (error) {
        console.error('Error starting bluetooth:', error);
        return { status: 'error' };
      }
    },
  /**
   * Pobiera aktualne wartości czujników
   */
  async getSensors() {
    try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/sensors`);
      if (!response.ok) throw new Error('Failed to fetch sensors');
      return await response.json();
    } catch (error) {
      console.error('Error fetching sensors:', error);
      return { temperature: null, humidity: null };
    }
  },
  async watering() {
    try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/watering`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) throw new Error('Failed to trigger watering');
      return await response.json();
    } catch (error) {
      console.error('Error triggering watering:', error);
      return { status: 'error' };
    }
  },
  /**
   * Pobiera status wszystkich urządzeń
   */
  async getStatus() {
    try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/status`);
      if (!response.ok) throw new Error('Failed to fetch status');
      return await response.json();
    } catch (error) {
      console.error('Error fetching status:', error);
      return { 
        fan: false, 
        light: false, 
        pump: false, 
        heater: false,
        sprinkler: false,
        manual_mode: false
      };
    }
  },

  

  /**
   * Steruje konkretnym urządzeniem
   * @param {string} device - 'fan', 'light', 'pump', 'sprinkler', 'heater', 'manual_mode'
   * @param {string} state - 'on' lub 'off'
   */
  async toggleDevice(device, state) {
    try {
      const response = await fetchWithTimeout(
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
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/settings`);
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
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/settings`, {
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
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/watering-timer`);
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




};

export default apiService;