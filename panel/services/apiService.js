
// services/apiService.js
// Usługa do komunikacji z backendem IoT

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Helper: fetch z timeoutem
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
  // Uruchamia BluetoothService na backendzie
  async startBluetooth() {
    try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/bluetooth`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!response.ok) throw new Error('Failed to start Bluetooth');
      return await response.json();
    } catch (error) {
      console.error('Error starting Bluetooth:', error);
      return { status: 'error' };
    }
  },

  // Pobiera aktualne wartości czujników
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

  // Pobiera status wszystkich urządzeń
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

  // Steruje konkretnym urządzeniem
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

  // Pobiera aktualne ustawienia docelowe
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

  // Aktualizuje ustawienia docelowe
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

  // Pobiera harmonogram światła z settings
  async getLightSchedule() {
    try {
      const settings = await this.getSettings();
      return {
        light_hours: settings.light_hours || 12,
        start_hour: settings.start_hour || 6,
        start_minute: settings.start_minute || 0,
        end_hour: settings.end_hour || 18,
        end_minute: settings.end_minute || 0
      };
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

  // Pobiera dni podlewania
  async getWateringDays() {
    try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/settings`);
      if (!response.ok) throw new Error('Failed to fetch settings');
      const data = await response.json();
      const DAY_NAMES = ['SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY'];
      const mappedDays = (data.watering_days || []).map(num => DAY_NAMES[num] || `DAY_${num}`);
      return {
        watering_days: mappedDays,
        watering_time: data.watering_time || '09:00',
        water_seconds: data.water_seconds || 30
      };
    } catch (error) {
      console.error('Error fetching watering days:', error);
      return {
        watering_days: [],
        watering_time: '09:00',
        water_seconds: 30
      };
    }
  },

  // Włącza podlewanie (pompa na water_seconds, potem auto-wyłącza)
  async watering() {
    try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/watering`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!response.ok) throw new Error('Failed to trigger watering');
      return await response.json();
    } catch (error) {
      console.error('Error triggering watering:', error);
      return { status: 'error' };
    }
  },
};

export default apiService;