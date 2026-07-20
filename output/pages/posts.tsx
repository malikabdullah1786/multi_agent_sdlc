import Layout from '../components/Layout';
import PostList from '../components/PostList';

const PostsPage = () => {
  return (
    <Layout>
      <h1>Posts</h1>
      <PostList />
    </Layout>
  );
};

export default PostsPage;