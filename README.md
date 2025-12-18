# LeafCore Panel

Plant monitor application built with React Native and Expo. Displays real-time environmental metrics with beautiful circular gauges.

## Features

- 📊 Real-time temperature monitoring (°C)
- 💧 Humidity level display (%)
- 💡 Light status and scheduling
- 🚿 Watering schedule with countdown timer
- 📱 Responsive layout optimized for 1024x600 screens
- 🎨 Modern dark theme UI with custom circular gauges

## Installation

```bash
npm install
```

## Development

Run the app on web:

```bash
npm run web
```

Run on Android:

```bash
npm run android
```

Run on iOS:

```bash
npm run ios
```

## Project Structure

- `App.js` - Main application component
- `components/` - Reusable React components
  - `CircularGauge.js` - SVG-based circular gauge component
  - `LightPanel.js` - Light status panel
  - `WateringPanel.js` - Watering schedule panel

## Technologies

- React Native
- Expo
- React Native SVG
- Expo Status Bar

## Screen Size

Optimized for landscape orientation on 1024x600 pixel screens.

## License

MIT
