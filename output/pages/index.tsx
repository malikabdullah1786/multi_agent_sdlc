import Layout from '../components/Layout';
import PostForm from '../components/PostForm';
import PostList from '../components/PostList';

const HomePage = () => {
  return (
    <Layout>
      <h1>Welcome to the homepage</h1>
      <PostForm />
      <PostList />
    </Layout>
  );
};

export default HomePage;