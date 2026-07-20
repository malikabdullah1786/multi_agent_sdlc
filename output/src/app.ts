
import express, { Request, Response } from 'express';
import { z } from 'zod';
import { Pool } from 'pg';

const app = express();
app.use(express.json());

const pool = new Pool({
  user: 'your_username',
  host: 'your_host',
  database: 'your_database',
  password: 'your_password',
  port: 5432,
});

// User schema
const userSchema = z.object({
  id: z.number().optional(),
  username: z.string().min(1),
  email: z.string().email(),
  password: z.string().min(8),
});

// Post schema
const postSchema = z.object({
  id: z.number().optional(),
  title: z.string().min(1),
  content: z.string().min(1),
  userId: z.number(),
});

// Comment schema
const commentSchema = z.object({
  id: z.number().optional(),
  content: z.string().min(1),
  postId: z.number(),
  userId: z.number(),
});

// Get all users
app.get('/users', async (req: Request, res: Response) => {
  try {
    const result = await pool.query('SELECT * FROM users');
    res.json(result.rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Internal Server Error' });
  }
});

// Get user by id
app.get('/users/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);
    const result = await pool.query('SELECT * FROM users WHERE id = $1', [id]);
    if (result.rows.length === 0) {
      res.status(404).json({ message: 'User not found' });
    } else {
      res.json(result.rows[0]);
    }
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Internal Server Error' });
  }
});

// Create new user
app.post('/users', async (req: Request, res: Response) => {
  try {
    const userData = userSchema.parse(req.body);
    const result = await pool.query(
      'INSERT INTO users (username, email, password) VALUES ($1, $2, $3) RETURNING *',
      [userData.username, userData.email, userData.password]
    );
    res.json(result.rows[0]);
  } catch (err) {
    console.error(err);
    if (err instanceof z.ZodError) {
      res.status(400).json({ message: 'Invalid request data' });
    } else {
      res.status(500).json({ message: 'Internal Server Error' });
    }
  }
});

// Get all posts
app.get('/posts', async (req: Request, res: Response) => {
  try {
    const result = await pool.query('SELECT * FROM posts');
    res.json(result.rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Internal Server Error' });
  }
});

// Get post by id
app.get('/posts/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);
    const result = await pool.query('SELECT * FROM posts WHERE id = $1', [id]);
    if (result.rows.length === 0) {
      res.status(404).json({ message: 'Post not found' });
    } else {
      res.json(result.rows[0]);
    }
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Internal Server Error' });
  }
});

// Create new post
app.post('/posts', async (req: Request, res: Response) => {
  try {
    const postData = postSchema.parse(req.body);
    const result = await pool.query(
      'INSERT INTO posts (title, content, user_id) VALUES ($1, $2, $3) RETURNING *',
      [postData.title, postData.content, postData.userId]
    );
    res.json(result.rows[0]);
  } catch (err) {
    console.error(err);
    if (err instanceof z.ZodError) {
      res.status(400).json({ message: 'Invalid request data' });
    } else {
      res.status(500).json({ message: 'Internal Server Error' });
    }
  }
});

// Get all comments
app.get('/comments', async (req: Request, res: Response) => {
  try {
    const result = await pool.query('SELECT * FROM comments');
    res.json(result.rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Internal Server Error' });
  }
});

// Get comment by id
app.get('/comments/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);
    const result = await pool.query('SELECT * FROM comments WHERE id = $1', [id]);
    if (result.rows.length === 0) {
      res.status(404).json({ message: 'Comment not found' });
    } else {
      res.json(result.rows[0]);
    }
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: 'Internal Server Error' });
  }
});

// Create new comment
app.post('/comments', async (req: Request, res: Response) => {
  try {
    const commentData = commentSchema.parse(req.body);
    const result = await pool.query(
      'INSERT INTO comments (content, post_id, user_id) VALUES ($1, $2, $3) RETURNING *',
      [commentData.content, commentData.postId, commentData.userId]
    );
    res.json(result.rows[0]);
  } catch (err) {
    console.error(err);
    if (err instanceof z.ZodError) {
      res.status(400).json({ message: 'Invalid request data' });
    } else {
      res.status(500).json({ message: 'Internal Server Error' });
    }
  }
});

app.listen(3000, () => {
  console.log('Server started on port 3000');
});
