import { NextApiRequest, NextApiResponse } from 'next';
import axios from 'axios';

const postsApi = async (req: NextApiRequest, res: NextApiResponse) => {
  if (req.method === 'GET') {
    try {
      const response = await axios.get('http://localhost:3000/api/posts');
      res.status(200).json(response.data);
    } catch (error) {
      res.status(500).json({ message: 'Error fetching posts' });
    }
  } else if (req.method === 'POST') {
    try {
      const response = await axios.post('http://localhost:3000/api/posts', req.body);
      res.status(201).json(response.data);
    } catch (error) {
      res.status(500).json({ message: 'Error creating post' });
    }
  } else {
    res.status(405).json({ message: 'Method not allowed' });
  }
};

export default postsApi;