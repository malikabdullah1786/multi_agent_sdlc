import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:3000/api',
});

export const postApi = async (data: any) => {
  try {
    const response = await api.post('/posts', data);
    return response.data;
  } catch (error: any) {
    throw error;
  }
};

export const getApi = async () => {
  try {
    const response = await api.get('/posts');
    return response.data;
  } catch (error: any) {
    throw error;
  }
};