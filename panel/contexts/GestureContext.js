import React, { createContext, useState, useCallback } from 'react';

export const GestureContext = createContext();

export const GestureProvider = ({ children }) => {
  const [isSliderActive, setIsSliderActive] = useState(false);

  const startSliderInteraction = useCallback(() => {
    setIsSliderActive(true);
  }, []);

  const endSliderInteraction = useCallback(() => {
    setIsSliderActive(false);
  }, []);

  return (
    <GestureContext.Provider
      value={{
        isSliderActive,
        startSliderInteraction,
        endSliderInteraction,
      }}
    >
      {children}
    </GestureContext.Provider>
  );
};

export const useGestureContext = () => {
  const context = React.useContext(GestureContext);
  if (!context) {
    throw new Error('useGestureContext must be used within GestureProvider');
  }
  return context;
};
