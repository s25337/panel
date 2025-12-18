# LeafCore Panel

Plant monitor application built with React Native and Expo. Displays real-time environmental metrics with beautiful circular gauges.

## Features

- 📊 Real-time temperature monitoring (°C) with interactive slider
- 💧 Humidity level display (%) with interactive slider
- 💡 Light status and scheduling
- 🚿 Watering schedule with countdown timer
- 📱 Responsive layout optimized for 1024x600 screens
- 🎨 Modern dark theme UI with custom circular gauges
- ☝️ Touch & mouse support for sliders (works on Safari, tablets, mobile)

## Requirements

- Node.js (v16 or higher)
- npm or yarn
- Expo CLI (installed globally or via npx)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/s25337/panel.git
cd panel
```

### 2. Install dependencies

```bash
npm install
```

This will install:
- `react` - UI library
- `react-native` - Cross-platform framework
- `expo` - Development platform
- `expo-status-bar` - Status bar management
- `react-native-svg` - SVG rendering for gauges

## Running the Application

### Web (Recommended for development)

```bash
npm run web
```

This will start the development server and open the app in your browser at `http://localhost:8081`

**Controls:**
- Click/tap on the circular gauges to adjust temperature and humidity values
- Works with mouse, touchpad, and touch screens

### Android

```bash
npm run android
```

Requires Android SDK and emulator/device setup.

### iOS

```bash
npm run ios
```

Requires Xcode and iOS simulator/device setup.

### Start with Expo

```bash
npm start
```

This opens the Expo menu where you can choose your platform.

## Project Structure

```
panel/
├── App.js                          # Main application component
├── components/
│   ├── CircularGauge.js           # Interactive SVG gauge component
│   ├── LightPanel.js              # Light status panel
│   └── WateringPanel.js           # Watering schedule panel
├── assets/                         # Image assets
├── package.json                    # Dependencies
├── app.json                        # Expo configuration
├── index.js                        # Entry point
├── .babelrc                        # Babel configuration
├── .gitignore                      # Git ignore rules
└── README.md                       # This file
```

## Technologies

- **React Native** - Cross-platform UI framework
- **Expo** - Development and deployment platform
- **React Native SVG** - Vector graphics rendering
- **JavaScript (ES6+)** - Programming language

## Features Details

### CircularGauge Component
- Displays a value between 0 and maxValue
- Shows unit (°C, %)
- Interactive slider controlled by mouse or touch
- Smooth arc animation

### LightPanel Component
- Displays light status (On/Off)
- Shows scheduling information
- Custom SVG light bulb icon

### WateringPanel Component
- Live countdown timer (days:hours:minutes:seconds)
- Water tank capacity display
- Updates every second
- Custom SVG water drop icon

## Customization

### Change Theme Colors

Edit `App.js` and modify the color values:
- Background: `#1a1a1a`
- Panel background: `#252525`
- Temperature gauge: `#FF6B6B`
- Humidity gauge: `#4ECDC4`
- Light gauge: `#D4A574`
- Watering gauge: `#5DADE2`

### Adjust Screen Size

Edit `app.json` to change target orientation or screen dimensions.

### Update Values

The default values are in `App.js`:
- Temperature: 28°C
- Humidity: 30%
- Light schedule: 18:00 - 06:00
- Watering countdown: 2d 10h 54m 33s
- Water tank: 200ml

## Browser Compatibility

- ✅ Chrome/Chromium (web)
- ✅ Safari (web)
- ✅ Firefox (web)
- ✅ Mobile browsers
- ✅ Tablets (iPad, Android)

## Development

### Building for production

```bash
npm run build
```

### Linting

```bash
npm run lint
```
