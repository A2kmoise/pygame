import sys
import random
import pygame
import os

# Small-phone portrait window (simulates ~360x640 phone screen)
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 450
FPS = 60

# Colors
COLOR_BG = (20, 20, 28)
COLOR_GROUND = (44, 44, 60)
COLOR_PLAYER = (230, 230, 255)
COLOR_OBSTACLE = (255, 90, 90)
COLOR_UI = (200, 200, 220)
COLOR_CLOUD = (80, 80, 110)

# Gameplay constants
GROUND_HEIGHT = 70
PLAYER_WIDTH = 40
PLAYER_HEIGHT = 48
PLAYER_START_X = 100
GRAVITY = 0.9
JUMP_VELOCITY = -16.0
BASE_SCROLL_SPEED = 2.0
MAX_SCROLL_SPEED = 10.0
SPEEDUP_EVERY_SECONDS = 1.0
# Alternate gaps: small then big, repeatedly
SMALL_GAP_PX = 360
BIG_GAP_PX = 500
OBSTACLE_MIN_WIDTH = 24
OBSTACLE_MAX_WIDTH = 42
OBSTACLE_MIN_HEIGHT = 60
OBSTACLE_MAX_HEIGHT = 60
CLOUD_SPEED = 0.5

pygame.init()
# Music setup (bg1..bg5 in order; bg6 on game over)
MUSIC_ENABLED = False
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_FILES = [
	os.path.join(SCRIPT_DIR, "bg1.mp3"),
	os.path.join(SCRIPT_DIR, "bg2.mp3"),
	os.path.join(SCRIPT_DIR, "bg3.mp3"),
	os.path.join(SCRIPT_DIR, "bg4.mp3"),
	os.path.join(SCRIPT_DIR, "bg5.mp3"),
]
GAME_OVER_MUSIC = os.path.join(SCRIPT_DIR, "bg6.mp3")
try:
	pygame.mixer.init()
	MUSIC_ENABLED = True
except Exception:
	MUSIC_ENABLED = False
MUSIC_END = pygame.USEREVENT + 7
if MUSIC_ENABLED:
	pygame.mixer.music.set_endevent(MUSIC_END)
_current_track_index = 0

# Optional SFX with 0.5s cooldown
SFX_ENABLED = MUSIC_ENABLED
JUMP_SFX = None
JUMP_SFX_COOLDOWN_MS = 500
_last_jump_sfx_ms = -JUMP_SFX_COOLDOWN_MS
try:
	jump_path = os.path.join(SCRIPT_DIR, "jump.wav")
	if os.path.exists(jump_path) and MUSIC_ENABLED:
		JUMP_SFX = pygame.mixer.Sound(jump_path)
		JUMP_SFX.set_volume(0.7)
except Exception:
	JUMP_SFX = None

def play_jump_sfx():
	global _last_jump_sfx_ms
	if not (SFX_ENABLED and JUMP_SFX):
		return
	now = pygame.time.get_ticks()
	if now - _last_jump_sfx_ms >= JUMP_SFX_COOLDOWN_MS:
		_last_jump_sfx_ms = now
		try:
			JUMP_SFX.play()
		except Exception:
			pass

def play_next_track():
	global _current_track_index
	if not MUSIC_ENABLED:
		return
	try:
		if _current_track_index >= len(MUSIC_FILES):
			_current_track_index = len(MUSIC_FILES) - 1
		pygame.mixer.music.load(MUSIC_FILES[_current_track_index])
		pygame.mixer.music.play()
		_current_track_index = min(_current_track_index + 1, len(MUSIC_FILES))
	except Exception:
		pass


def start_music_sequence():
	global _current_track_index
	_current_track_index = 0
	play_next_track()


def play_game_over_music():
	if not MUSIC_ENABLED:
		return
	try:
		# Fade out current track over 0.5s, then play bg6 once
		pygame.mixer.music.fadeout(500)
		pygame.mixer.music.load(GAME_OVER_MUSIC)
		pygame.mixer.music.play()
	except Exception:
		pass

screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Jumping aviator")
clock = pygame.time.Clock()
font_large = pygame.font.SysFont(None, 48)
font_small = pygame.font.SysFont(None, 28)


def draw_text_center(text, font, color, surface, y):
	label = font.render(text, True, color)
	rect = label.get_rect(center=(WINDOW_WIDTH // 2, y))
	surface.blit(label, rect)


class Player:
	def __init__(self):
		self.width = PLAYER_WIDTH
		self.height = PLAYER_HEIGHT
		self.x = PLAYER_START_X
		self.ground_y = WINDOW_HEIGHT - GROUND_HEIGHT - self.height
		self.y = float(self.ground_y)
		self.vertical_velocity = 0.0
		self.is_on_ground = True
		# Load player image (scaled), fallback to None
		self.image = None
		player_img_path = os.path.join(SCRIPT_DIR, "player.png")
		try:
			img = pygame.image.load(player_img_path).convert_alpha()
			self.image = pygame.transform.smoothscale(img, (self.width, self.height))
		except Exception:
			self.image = None
		self.rect = pygame.Rect(self.x, int(self.y), self.width, self.height)

	def try_jump(self):
		if self.is_on_ground:
			self.vertical_velocity = JUMP_VELOCITY
			self.is_on_ground = False
			play_jump_sfx()

	def update(self):
		self.vertical_velocity += GRAVITY
		self.y += self.vertical_velocity
		if self.y >= self.ground_y:
			self.y = float(self.ground_y)
			self.vertical_velocity = 0.0
			self.is_on_ground = True
		self.rect.update(self.x, int(self.y), self.width, self.height)

	def draw(self, surface):
		if self.image is not None:
			surface.blit(self.image, (self.rect.x, self.rect.y))
		else:
			pygame.draw.rect(surface, COLOR_PLAYER, self.rect, border_radius=6)


class Obstacle:
	def __init__(self, x, width, height):
		self.width = width
		self.height = height
		self.x = float(x)
		self.y = WINDOW_HEIGHT - GROUND_HEIGHT - height
		self.rect = pygame.Rect(int(self.x), int(self.y), self.width, self.height)

	def update(self, scroll_speed):
		self.x -= scroll_speed
		self.rect.update(int(self.x), int(self.y), self.width, self.height)

	def draw(self, surface):
		pygame.draw.rect(surface, COLOR_OBSTACLE, self.rect, border_radius=4)

	@property
	def is_offscreen(self):
		return self.rect.right < 0


class Cloud:
	def __init__(self):
		self.reset(random.uniform(0, WINDOW_WIDTH))

	def reset(self, x=None):
		self.x = float(x if x is not None else WINDOW_WIDTH + random.randint(0, 120))
		self.y = random.randint(30, WINDOW_HEIGHT // 2)
		self.width = random.randint(50, 110)
		self.height = random.randint(18, 30)

	def update(self, dt):
		self.x -= CLOUD_SPEED * dt
		if self.x + self.width < 0:
			self.reset()

	def draw(self, surface):
		rect = pygame.Rect(int(self.x), int(self.y), self.width, self.height)
		pygame.draw.ellipse(surface, COLOR_CLOUD, rect)


class Game:
	def __init__(self):
		self.reset()

	def reset(self):
		self.player = Player()
		self.obstacles = []
		self.distance_since_last_spawn = 0.0
		self.next_gap_is_big = False
		self.scroll_speed = BASE_SCROLL_SPEED
		self.distance_travelled_px = 0.0
		self.elapsed_time = 0.0
		self.game_over = False
		self.music_locked = False
		self.clouds = [Cloud() for _ in range(5)]
		start_music_sequence()

	def increase_difficulty(self, dt):
		# Faster acceleration curve to hit a higher top speed sooner
		self.elapsed_time += dt
		seconds_to_max = 25.0
		linear_progress = min(1.0, self.elapsed_time / seconds_to_max)
		self.scroll_speed = BASE_SCROLL_SPEED + (MAX_SCROLL_SPEED - BASE_SCROLL_SPEED) * linear_progress

	def spawn_obstacle_if_needed(self, dt):
		self.distance_since_last_spawn += self.scroll_speed
		gap_target = BIG_GAP_PX if self.next_gap_is_big else SMALL_GAP_PX
		if self.distance_since_last_spawn >= gap_target:
			width = random.randint(OBSTACLE_MIN_WIDTH, OBSTACLE_MAX_WIDTH)
			height = random.randint(OBSTACLE_MIN_HEIGHT, OBSTACLE_MAX_HEIGHT)
			x = WINDOW_WIDTH + 10
			self.obstacles.append(Obstacle(x, width, height))
			self.distance_since_last_spawn = 0.0
			self.next_gap_is_big = not self.next_gap_is_big

	def handle_input(self, event):
		if event.type == pygame.KEYDOWN:
			if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
				self.player.try_jump()
		elif event.type == pygame.MOUSEBUTTONDOWN:
			self.player.try_jump()

	def update(self, dt):
		if self.game_over:
			return
		self.increase_difficulty(dt)
		self.player.update()
		for obstacle in list(self.obstacles):
			obstacle.update(self.scroll_speed)
			if obstacle.is_offscreen:
				self.obstacles.remove(obstacle)
		self.spawn_obstacle_if_needed(dt)
		self.distance_travelled_px += self.scroll_speed
		for obstacle in self.obstacles:
			if self.player.rect.colliderect(obstacle.rect):
				self.game_over = True
				if MUSIC_ENABLED and not self.music_locked:
					self.music_locked = True
					play_game_over_music()
				break

	def draw_ground(self, surface):
		ground_rect = pygame.Rect(0, WINDOW_HEIGHT - GROUND_HEIGHT, WINDOW_WIDTH, GROUND_HEIGHT)
		pygame.draw.rect(surface, COLOR_GROUND, ground_rect)

	def draw_hud(self, surface):
		score = int(self.distance_travelled_px // 10)
		score_surf = font_small.render(f"Score: {score}", True, COLOR_UI)
		surface.blit(score_surf, (12, 10))
		spd_surf = font_small.render(f"Speed: {self.scroll_speed:.1f}", True, COLOR_UI)
		surface.blit(spd_surf, (12, 36))

	def draw(self, surface):
		surface.fill(COLOR_BG)
		for cloud in self.clouds:
			cloud.draw(surface)
		for obstacle in self.obstacles:
			obstacle.draw(surface)
		self.draw_ground(surface)
		self.player.draw(surface)
		self.draw_hud(surface)
		if self.game_over:
			draw_text_center("Game Over", font_large, COLOR_UI, surface, WINDOW_HEIGHT // 2 - 20)
			draw_text_center("Tap/Space to restart", font_small, COLOR_UI, surface, WINDOW_HEIGHT // 2 + 26)

	def update_clouds(self, dt):
		for cloud in self.clouds:
			cloud.update(dt)


def main():
	game = Game()
	accumulator_ms = 0.0
	while True:
		dt_ms = clock.tick(FPS)
		dt = dt_ms / 1000.0
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				pygame.quit()
				sys.exit()
			if MUSIC_ENABLED and event.type == MUSIC_END and not game.game_over:
				play_next_track()
			if game.game_over:
				if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
					game.reset()
			else:
				game.handle_input(event)
		game.update_clouds(dt_ms)
		game.update(dt)
		game.draw(screen)
		pygame.display.flip()


if __name__ == "__main__":
	main()