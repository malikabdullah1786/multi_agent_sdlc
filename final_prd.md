# Product Requirements Document

## 1. Overview & Goals
* **Core Problem**: Lack of a lightweight, browser-accessible arcade experience for quick engagement.
* **User Benefit**: Instant access to a physics-based skill game with persistent progress tracking.
* **KPIs**: Average Session Duration (ASD), High Score Distribution, Retention Rate (Daily).

## 2. Personas (Compact)
* **Casual Gamer**: Wants a low-friction, "one-more-try" loop to kill time.
* **Competitive User**: Aims to beat personal and global-style records via persistent storage.

## 3. User Stories & Epics (Dense List)
* **[Core Gameplay]** As a user, I want physics-based movement so the game feels authentic.
  - AC: [1] Given game start, When Space/Click, Then bird Y-velocity increases upward. [2] Given flight, When idle, Then gravity constant pulls bird downward. [3] Given collision with pipe/ground, Then trigger Game Over state.
* **[Obstacle System]** As a user, I want randomized pipes to provide a challenge.
  - AC: [1] Given pipe spawn, When interval reached, Then generate pipe pair with random gap height. [2] Given pipe exit screen, Then remove object from memory.
* **[Progression]** As a user, I want to track my score so I can measure improvement.
  - AC: [1] Given pipe passed, When bird X > pipe X, Then increment score by 1. [2] Given game over, When current score > localStorage.highScore, Then update localStorage.

## 4. Functional Specs (Bullet Tree)
* **Game Engine (HTML5 Canvas)**
    * **Physics Loop**: `requestAnimationFrame` @ 60fps.
    * **Gravity**: Constant acceleration applied to `bird.velocity` every frame.
    * **Input**: Event listeners for `keydown` (Space) and `mousedown`.
* **Entity Management**
    * **Bird**: Object with `x, y, width, height, velocity`.
    * **Pipes**: Array of objects with `x, topHeight, bottomY`.
    * **Collision**: AABB (Axis-Aligned Bounding Box) check between Bird and Pipes/Ground.
* **State Management**
    * **States**: `START` $\rightarrow$ `PLAYING` $\rightarrow$ `GAME_OVER`.
    * **Score**: Integer variable; persists to `localStorage` on `GAME_OVER`.
    * **Reset**: `gameState = START` $\rightarrow$ Clear pipe array $\rightarrow$ Reset bird position.
* **Error Handling**
    * **LocalStorage Access** $\rightarrow$ Success: Load High Score, Error: Default to 0.
    * **Canvas Render** $\rightarrow$ Success: Draw frame, Error: Log console error, maintain last state.

## 5. Non-Functional Requirements
* **Performance**: Frame time $< 16.67\text{ms}$ (stable 60fps) on mid-range hardware.
* **Compatibility**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+ (Desktop).
* **Responsiveness**: Canvas scales to maintain aspect ratio via CSS `max-width: 100%`.
* **Security**: No server-side data; `localStorage` used exclusively for client-side persistence.

## 6. Out of Scope & Release Plan
* **Out of Scope**: Multiplayer/Leaderboards, Sound Effects/Music, Mobile Touch-specific optimizations.
* **Release Plan**:
    1. **Alpha**: Core physics and collision loop verification.
    2. **Beta**: High score persistence and UI polish.
    3. **GA**: Deployment to static hosting (e.g., GitHub Pages/Vercel).