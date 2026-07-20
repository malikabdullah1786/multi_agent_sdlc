import { useForm } from 'react-hook-form';
import axios from 'axios';

interface CreatePostFormProps {
  title: string;
  content: string;
}

const CreatePostForm = () => {
  const { register, handleSubmit, errors } = useForm<CreatePostFormProps>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const onSubmit = async (data: CreatePostFormProps) => {
    setLoading(true);
    try {
      await axios.post('/api/posts', data);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <label>Title:</label>
      <input type="text" {...register('title')} />
      {errors.title && <div>{errors.title.message}</div>}

      <label>Content:</label>
      <textarea {...register('content')} />
      {errors.content && <div>{errors.content.message}</div>}

      <button type="submit">Create Post</button>
    </form>
  );
};

export default CreatePostForm;