import { useForm } from 'react-hook-form';
import axios from 'axios';

const PostForm = () => {
  const { register, handleSubmit, errors } = useForm();
  const onSubmit = async (data: any) => {
    try {
      const response = await axios.post('/api/posts', data);
      console.log(response);
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <label>Title:</label>
      <input type="text" {...register('title')} />
      {errors.title && <div>This field is required</div>}
      <label>Content:</label>
      <textarea {...register('content')} />
      {errors.content && <div>This field is required</div>}
      <button type="submit">Create Post</button>
    </form>
  );
};

export default PostForm;