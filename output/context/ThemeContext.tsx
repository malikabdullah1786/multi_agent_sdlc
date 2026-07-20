import { createContext, useState } from 'react';

interface ThemeContextProps {
  children: React.ReactNode;
}

const ThemeContext = createContext({}
  as {
    darkMode: boolean;
    toggleDarkMode: () => void;
  }
);

const ThemeProvider = ({ children }: ThemeContextProps) => {
  const [darkMode, setDarkMode] = useState(false);

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
  };

  return (
    <ThemeContext.Provider value={{ darkMode, toggleDarkMode }}>
      {children}
    </ThemeContext.Provider>
  );
};

export { ThemeContext, ThemeProvider };