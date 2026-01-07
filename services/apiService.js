// services/apiService.js
// Usługa do komunikacji z backend'em IoT

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

export const apiService = {
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
};

export default apiService;
