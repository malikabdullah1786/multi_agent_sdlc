import { useContext } from 'react';
import { ThemeContext } from '../context/ThemeContext';
import Header from './Header';
import Footer from './Footer';

const Layout = ({ children }: { children: React.ReactNode }) => {
  const { darkMode } = useContext(ThemeContext);

  return (
    <div className={darkMode ? 'dark' : 'light'}>
      <Header />
      <main>{children}</main>
      <Footer />
    </div>
  );
};

export default Layout;