import Link from 'next/link';
import { useContext } from 'react';
import { ThemeContext } from '../context/ThemeContext';

const Header = () => {
  const { darkMode, toggleDarkMode } = useContext(ThemeContext);

  return (
    <header>
      <nav>
        <Link href="/">Home</Link>
        <Link href="/posts">Posts</Link>
        <button onClick={toggleDarkMode}>Toggle Dark Mode</button>
      </nav>
    </header>
  );
};

export default Header;