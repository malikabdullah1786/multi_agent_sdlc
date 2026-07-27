# Product Requirements Document

## Overview & Goals
* **Core Problem**: Lack of a personalized, offline-capable Bubble Shooter game for Android.
* **User Benefit**: High-engagement casual gaming experience tailored for personal use.
* **KPIs**: Frame rate $\ge$ 60fps; Zero crash rate during core gameplay loop; Load time $< 2s$.

## Personas (Compact)
* **Solo Player**: Wants a seamless, distraction-free bubble-shooting experience on an Android device.

## User Stories & Epics (Dense List)
* **[Core Gameplay]** As a player, I want to shoot colored bubbles to match 3+ so that I can clear the board.
  - AC: [1] Given bubble fired, When it hits 2+ of same color, Then pop all 3+ bubbles. [2] Given bubble hits wall, When it reflects, Then change trajectory based on angle. [3] Given bubble hits ceiling, When it stops, Then snap to grid.
* **[Game Logic]** As a player, I want bubbles to fall if disconnected from the ceiling so that the board clears.
  - AC: [1] Given a cluster is not connected to top row, When a match occurs, Then drop all disconnected bubbles.
* **[Level System]** As a player, I want progressive difficulty so that the game remains challenging.
  - AC: [1] Given level completion, When starting next level, Then increase bubble density/color variety.
* **[UI/UX]** As a player, I want a score tracker and game-over state so that I can track progress.
  - AC: [1] Given bubble pop, When points added, Then update score UI. [2] Given bubbles reach bottom line, When collision occurs, Then trigger Game Over.

## Functional Specs (Bullet Tree)
* **Game Engine (React Native + Canvas/SVG)**
  * **Physics Engine**: 2D collision detection (Circle-Circle); Reflection vectors for wall bounces.
  * **Grid System**: Hexagonal coordinate system for bubble positioning.
  * **Bubble Spawner**: Random color generator based on current level palette.
* **Core Screens**
  * **Main Menu**: [Start Game] -> Success: Navigate to GameScreen, Error: Log failure.
  * **Game Screen**: 
    * **Aiming Line**: Dynamic vector line following touch/drag.
    * **Bubble Launcher**: Fixed bottom-center position; rotates based on touch input.
    * **Game Board**: Top-down container for bubble clusters.
* **Game Rules/Validations**
  * **Match Logic**: Recursive flood-fill algorithm to identify contiguous colors.
  * **Win Condition**: All bubbles cleared from board.
  * **Loss Condition**: Any bubble crosses the bottom boundary.

## Non-Functional Requirements
* **Performance**: Maintain 60 FPS using `react-native-reanimated` or `Canvas` to avoid JS bridge bottlenecks.
* **Compatibility**: Android 10+ (API Level 29+); Support for various screen aspect ratios (Responsive Layout).
* **Persistence**: Local storage (AsyncStorage) for high scores and level progress.
* **Input Latency**: Touch-to-fire latency $< 16ms$.

## Out of Scope & Release Plan
* **Exclusions**: Online multiplayer, In-app purchases (IAP), Cloud save/Account sync.
* **Deployment**:
  1. **Alpha**: Core physics and matching logic verified on emulator.
  2. **Beta**: Level progression and UI polish on physical Android device.
  3. **Release**: Final APK build for personal installation.