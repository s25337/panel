import React from 'react';
import { registerRootComponent } from 'expo';
import App from './App';

// Dodaj CSS, aby nie dało się zaznaczać tekstu
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    * {
      user-select: none;
      -webkit-user-select: none;
      -moz-user-select: none;
      -ms-user-select: none;
    }
  `;
  document.head.appendChild(style);
}

registerRootComponent(App);
