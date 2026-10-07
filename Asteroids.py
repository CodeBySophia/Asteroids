import os
import math
import random
import csv
from datetime import datetime

import pyglet
from pyglet.window import key
from pyglet.window import mouse

# Constants
SET_WIDTH = 1400  # starting window size in pixels
SET_HEIGHT = 700  # starting window size in pixels
MIN_WIDTH = 640  # smallest allowed window size in pixels
MIN_HEIGHT = 480
WIDTH = SET_WIDTH  # current play area size, updated whenever the window is resized
HEIGHT = SET_HEIGHT
ROTATION_SPEED = 220  # degrees per second
ACCELERATION = 300  # pixels per second squared
DECELERATION = 100  # pixels per second squared, slows the drifting ship when not thrusting
SLOWDOWN_RATE = 200  # rate at which the ship slows down when the down key is pressed
MAX_SHIP_SPEED = 500  # pixels per second
SHIP_INVULNERABLE_TIME = 2  # seconds of protection after the ship appears
SHIP_BLINK_RATE = 10  # blinks per second while the ship is invulnerable
MIN_METEOR_SCALE = 0.4  # minimum scale for meteors
MAX_METEOR_SCALE = 1.0  # maximum scale for meteors
MIN_METEOR_SPEED = 50  # minimum speed of meteors in pixels per second
MAX_METEOR_SPEED = 150  # maximum speed of meteors in pixels per second
METEOR_SPLIT_SCALE = 0.5  # meteors at least this big break into two pieces when hit
METEOR_SPLIT_FACTOR = 0.55  # scale of a piece relative to the original meteor
METEOR_SPLIT_SPEEDUP = 1.3  # pieces fly faster than the original meteor
METEOR_SPAWN_INTERVAL = 1  # seconds between new meteors at level 1 in the starting window size
MIN_METEOR_SPAWN_INTERVAL = 0.3  # meteors never appear more often than this (before window size scaling)
METEOR_SPAWN_LEVEL_FACTOR = 0.9  # the spawn interval is multiplied by this with each level
METEOR_SPEED_PER_LEVEL = 0.1  # meteors get 10 % faster with each level...
MAX_METEOR_SPEED_FACTOR = 2.5  # ...but at most 2.5 times faster
MIN_AREA_FACTOR = 0.5  # small windows don't get fewer meteors than half the usual amount
STARTING_LIVES = 3  # starting number of lives
BULLET_SPEED = 700  # speed of bullets in pixels per second
ENEMY_BULLET_SPEED = BULLET_SPEED / 4  # UFO bullets are slower
UFO_SPEED = 100
UFO_LEVEL = 5  # level from which UFOs start to appear
UFO_SPAWN_INTERVAL = 20  # seconds between UFO spawns
UFO_SHOOT_INTERVAL = 4  # seconds between UFO shots
FONT = 'arial'
LOST_LIFE_TEXT = "LIFE LOST"
PAUSE_KEYS = (key.P, key.ESCAPE)
POINTS_DISPLAY_TIME = 2  # time in seconds to display the points message
POINTS = 100  # Basic value of points
MAX_NAME_LENGTH = 15
SCORES_FILE = 'scores.csv'

# Hitboxes: collision radius = HITBOX * average half-size of the sprite
SHIP_HITBOX = 0.75
METEOR_HITBOX = 0.95
BULLET_HITBOX = 0.6
UFO_HITBOX = 0.9

# File paths are resolved relative to the script's folder,
# so the game can be launched from anywhere.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def asset(*parts):
    return os.path.join(BASE_DIR, *parts)


# Window creation – resizable, so it can also be maximized or resized by dragging its edge
window = pyglet.window.Window(width=WIDTH, height=HEIGHT, resizable=True, caption='Asteroids')
window.set_minimum_size(MIN_WIDTH, MIN_HEIGHT)

# Load background image
background_image = pyglet.image.load(asset('imgs', 'background.jpg'))
background_sprite = pyglet.sprite.Sprite(background_image, x=0, y=0)


def update_background():
    # Scale background to fit the window
    background_sprite.scale_x = window.width / background_image.width
    background_sprite.scale_y = window.height / background_image.height


def load_centered(name):
    """Load an image and set its anchor point to the center."""
    img = pyglet.image.load(asset('imgs', name))
    img.anchor_x = img.width // 2
    img.anchor_y = img.height // 2
    return img


# Load images
SHIP_img1 = load_centered('ship.png')

THRUSTER_img = pyglet.image.load(asset('imgs', 'thruster.png'))
THRUSTER_img.anchor_x = THRUSTER_img.width // 2
THRUSTER_img.anchor_y = 0  # Thruster will be shown behind the ship

UFO_imgs = [load_centered(f'ufo{color}.png') for color in ('Blue', 'Green', 'Red', 'Yellow')]

MET_imgs = [load_centered(f'meteor{color}_big{i}.png')
            for color in ('Brown', 'Grey') for i in range(1, 5)]

BULLET_imgs = [load_centered(f'laser{color}.png') for color in ('Blue', 'Green', 'Red')]


# Load sounds – if a sound fails to load, the game keeps running without it.
def load_sound(name):
    try:
        return pyglet.media.load(asset('sounds', name), streaming=False)
    except Exception:
        return None


def play(sound):
    if sound is not None:
        try:
            sound.play()
        except Exception:
            pass


SOUND_LASER = load_sound('laser.wav')
SOUND_EXPLOSION = load_sound('explosion.wav')
SOUND_LOST_LIFE = load_sound('lost_life.wav')

# Create batch object
batch = pyglet.graphics.Batch()


class SpaceObject:
    hitbox = 0.8  # each object type can override it

    def __init__(self, img, x, y, batch):
        self.sprite = pyglet.sprite.Sprite(img, x=x, y=y, batch=batch)
        self.velocity_x = 0
        self.velocity_y = 0

    def radius(self):
        # sprite.width and sprite.height already include the sprite's scale
        return self.hitbox * (self.sprite.width + self.sprite.height) / 4

    def collides_with(self, other_obj):
        if not self.sprite or not other_obj.sprite:
            return False

        distance = math.hypot(self.sprite.x - other_obj.sprite.x,
                              self.sprite.y - other_obj.sprite.y)
        return distance < self.radius() + other_obj.radius()

    def move(self, dt):
        self.sprite.x += self.velocity_x * dt
        self.sprite.y += self.velocity_y * dt

    def is_outside_window(self):
        return (self.sprite.x < 0 or self.sprite.x > WIDTH or
                self.sprite.y < 0 or self.sprite.y > HEIGHT)

    def remove_sprite(self):
        if self.sprite:  # Make sure the sprite exists before deleting it
            self.sprite.delete()
            self.sprite = None  # Set sprite to None for later checks


class Ship(SpaceObject):
    hitbox = SHIP_HITBOX

    def __init__(self, img, x, y, batch):
        super().__init__(img, x, y, batch)
        self.invulnerable = SHIP_INVULNERABLE_TIME  # seconds of protection left
        self.keys = {
            'left': False,
            'right': False,
            'up': False,
            'down': False
        }
        self.alive = True  # Check if the ship still exists

        # Create thruster sprite
        self.thruster_sprite = pyglet.sprite.Sprite(THRUSTER_img, x=x, y=y, batch=batch)
        self.thruster_sprite.visible = False

    def update(self, dt):
        if not self.alive:
            return

        # Handle rotation
        if self.keys['left']:
            self.sprite.rotation -= ROTATION_SPEED * dt
        if self.keys['right']:
            self.sprite.rotation += ROTATION_SPEED * dt

        radians = math.radians(self.sprite.rotation)

        # Thrust pushes the ship in the direction it is facing; without thrust
        # the ship keeps drifting (inertia) and only slowly loses speed
        slowdown = 0
        if self.keys['up']:
            self.velocity_x += ACCELERATION * dt * math.sin(radians)
            self.velocity_y += ACCELERATION * dt * math.cos(radians)
            self.thruster_sprite.visible = True
        else:
            slowdown += DECELERATION
            self.thruster_sprite.visible = False

        # Handle braking
        if self.keys['down']:
            slowdown += SLOWDOWN_RATE

        # Change the speed but keep the direction of the movement
        speed = math.hypot(self.velocity_x, self.velocity_y)
        new_speed = min(MAX_SHIP_SPEED, max(0, speed - slowdown * dt))
        if speed > 0:
            self.velocity_x *= new_speed / speed
            self.velocity_y *= new_speed / speed

        self.move(dt)

        # Wrap-around effect for ship
        self.sprite.x %= WIDTH
        self.sprite.y %= HEIGHT

        # Update thruster position based on the ship's position and rotation
        offset = self.sprite.height / 2 + 40  # Offset behind the ship, adjusted to fit image
        self.thruster_sprite.x = (self.sprite.x - offset * math.sin(radians)) % WIDTH
        self.thruster_sprite.y = (self.sprite.y - offset * math.cos(radians)) % HEIGHT
        self.thruster_sprite.rotation = self.sprite.rotation

        # Blink while invulnerable
        if self.invulnerable > 0:
            self.invulnerable -= dt
            self.sprite.visible = self.invulnerable <= 0 or int(self.invulnerable * SHIP_BLINK_RATE) % 2 == 0

    def can_be_hit(self):
        return self.alive and self.invulnerable <= 0

    def delete(self):
        self.alive = False  # Mark ship as inactive
        self.remove_sprite()
        if self.thruster_sprite:  # The thruster flame is deleted together with the ship
            self.thruster_sprite.delete()
            self.thruster_sprite = None


class Meteor(SpaceObject):
    hitbox = METEOR_HITBOX

    def __init__(self, img, x, y, vx, vy, batch, scale=None):
        super().__init__(img, x, y, batch)
        # Random meteor scale, unless it is a piece of a bigger meteor
        self.sprite.scale = scale or random.uniform(MIN_METEOR_SCALE, MAX_METEOR_SCALE)
        self.velocity_x = vx
        self.velocity_y = vy

    def split(self):
        """Return two smaller pieces flying apart, or nothing if the meteor is too small."""
        if self.sprite.scale < METEOR_SPLIT_SCALE:
            return []
        speed = math.hypot(self.velocity_x, self.velocity_y) * METEOR_SPLIT_SPEEDUP
        # velocity_from_angle measures the angle from the x axis, so use atan2(y, x)
        angle = math.degrees(math.atan2(self.velocity_y, self.velocity_x))
        pieces = []
        for side in (-1, 1):
            vx, vy = velocity_from_angle(speed, angle + side * random.uniform(20, 60))
            pieces.append(Meteor(self.sprite.image, self.sprite.x, self.sprite.y, vx, vy, batch,
                                 scale=self.sprite.scale * METEOR_SPLIT_FACTOR))
        return pieces

    def update(self, dt):
        self.move(dt)
        # Check whether the meteor has left the window
        if self.is_outside_window():
            self.delete()

    def delete(self):
        self.remove_sprite()
        if self in meteors:  # Remove the meteor from the meteor list
            meteors.remove(self)


class Bullet(SpaceObject):
    hitbox = BULLET_HITBOX
    speed = BULLET_SPEED

    def __init__(self, img_list, x, y, rotation, batch):
        # Pick a random image from the provided list
        super().__init__(random.choice(img_list), x, y, batch)
        self.sprite.rotation = rotation
        radians = math.radians(rotation)
        self.velocity_x = self.speed * math.sin(radians)
        self.velocity_y = self.speed * math.cos(radians)

    def update(self, dt):
        self.move(dt)
        # Check whether the bullet has left the window
        if self.is_outside_window():
            self.delete()

    def delete(self):
        self.remove_sprite()
        if self in bullets:  # Remove the bullet from the bullet list
            bullets.remove(self)


class EnemyBullet(Bullet):
    speed = ENEMY_BULLET_SPEED

    def update(self, dt):
        super().update(dt)

        # Check for collision with the player's ship
        if self.sprite and ship1.can_be_hit() and self.collides_with(ship1):
            self.delete()  # Remove the bullet
            lose_life()

    def delete(self):
        self.remove_sprite()
        if self in enemy_bullets:  # Remove the bullet from the enemy bullet list
            enemy_bullets.remove(self)


class Ufo(SpaceObject):
    hitbox = UFO_HITBOX

    def __init__(self, img_list, x, y, vx, vy, batch):
        super().__init__(random.choice(img_list), x, y, batch)
        self.sprite.scale = 0.5  # Fixed size
        self.velocity_x = vx
        self.velocity_y = vy
        # Schedule the method itself (not a lambda) so it can be unscheduled later
        pyglet.clock.schedule_interval(self.shoot, UFO_SHOOT_INTERVAL)

    def update(self, dt):
        self.move(dt)
        # Wrap-around effect for UFO
        self.sprite.x %= WIDTH
        self.sprite.y %= HEIGHT

    def shoot(self, dt=None):
        # Shoot only if the player's ship is alive and UFO still exists
        if ship1.alive and self.sprite and not paused:
            # Calculate the angle between the UFO and the player's ship
            dx = ship1.sprite.x - self.sprite.x
            dy = ship1.sprite.y - self.sprite.y
            angle = math.degrees(math.atan2(dx, dy))  # Angle in degrees

            # Create and shoot the bullet towards the player's ship
            enemy_bullets.append(EnemyBullet(BULLET_imgs, self.sprite.x, self.sprite.y, angle, batch))

    def delete(self):
        self.remove_sprite()
        if self in ufos:
            ufos.remove(self)
        pyglet.clock.unschedule(self.shoot)  # Cancel scheduled shooting when the UFO is destroyed


# Lists to hold game objects
meteors = []
bullets = []
ufos = []
enemy_bullets = []

# Global variables to track game state
ship1 = None
lives = STARTING_LIVES
life_sprites = []
player_name = ''
player_name_input = ''
waiting_for_name = False
game_over = False
life_lost = False
game_started = False  # Track if the game has started
paused = False
score = 0  # Variable to track the player's score
points_display_time = 0  # Time remaining to display points message
points_text = ''  # Text of the points message
level = 1
next_level_score = POINTS * POINTS


def create_ship():
    global ship1
    if ship1 is not None:
        ship1.delete()  # Delete the old ship along with its thruster flame
    ship1 = Ship(SHIP_img1, WIDTH // 2, HEIGHT // 2, batch)


def create_life_sprites():
    global life_sprites
    for life_sprite in life_sprites:
        life_sprite.delete()
    life_sprites = []
    for i in range(STARTING_LIVES):
        life_sprite = pyglet.sprite.Sprite(SHIP_img1, x=30 + i * 50, y=30, batch=batch)
        life_sprite.scale = 0.5
        life_sprites.append(life_sprite)


# Run scheduled tasks
def game_scheduled_tasks():
    pyglet.clock.schedule_interval(update, 1 / 30)  # 30 times per second
    schedule_next_meteor()
    pyglet.clock.schedule_interval(spawn_UFO, UFO_SPAWN_INTERVAL)


# Stop all scheduled tasks
def stop_all_scheduled_tasks():
    pyglet.clock.unschedule(update)
    pyglet.clock.unschedule(spawn_meteor)
    pyglet.clock.unschedule(spawn_UFO)


def clear_objects():
    """Delete all meteors, bullets and UFOs – including their sprites."""
    # Iterate over a copy of the list ([:]) because delete() removes items from it
    for obj in meteors[:] + bullets[:] + ufos[:] + enemy_bullets[:]:
        obj.delete()
    meteors.clear()
    bullets.clear()
    ufos.clear()
    enemy_bullets.clear()


def restart_after_life_lost():
    global life_lost, points_display_time

    stop_all_scheduled_tasks()
    clear_objects()
    create_ship()
    life_lost = False
    points_display_time = 0
    game_scheduled_tasks()


def reset_game():
    global game_over, life_lost, game_started, paused, points_display_time, score, lives, level, next_level_score

    stop_all_scheduled_tasks()
    clear_objects()
    create_ship()
    create_life_sprites()

    # Reset game state variables
    game_over = False
    life_lost = False
    paused = False
    points_display_time = 0
    score = 0
    lives = STARTING_LIVES
    level = 1
    next_level_score = POINTS * POINTS
    game_started = True  # Ensure the game starts after reset

    game_scheduled_tasks()


def lose_life():
    """Shared logic for the ship being hit by a meteor or a UFO bullet."""
    global lives, life_lost

    lives -= 1
    if life_sprites:
        life_sprites.pop().delete()  # Remove one life indicator
    ship1.delete()
    play(SOUND_LOST_LIFE)

    if lives > 0:
        life_lost = True
    else:
        end_game()


def end_game():
    global game_over, top_scores
    game_over = True
    stop_all_scheduled_tasks()
    clear_objects()
    if player_name:
        export_score(player_name, score)
        top_scores = get_top_scores()


def add_points(points):
    global score, level, next_level_score, points_display_time, points_text
    score += points

    # Check whether to level up
    while score >= next_level_score:
        level += 1
        next_level_score += POINTS * POINTS  # Set the threshold for the next level

    # Show the points
    points_display_time = POINTS_DISPLAY_TIME
    points_text = f'Points: {points}'


def random_edge_position():
    """Return a random point on the window edge and an angle (in degrees) pointing inward."""
    edge = random.choice(['top', 'bottom', 'left', 'right'])
    if edge == 'top':
        return random.randint(0, WIDTH), HEIGHT, random.uniform(210, 330)
    if edge == 'bottom':
        return random.randint(0, WIDTH), 0, random.uniform(30, 150)
    if edge == 'left':
        return 0, random.randint(0, HEIGHT), random.uniform(300, 420) % 360
    return WIDTH, random.randint(0, HEIGHT), random.uniform(120, 240)


def velocity_from_angle(speed, angle):
    angle_rad = math.radians(angle)
    return speed * math.cos(angle_rad), speed * math.sin(angle_rad)


def meteor_spawn_interval():
    """Meteors come more often with higher levels and in bigger windows."""
    interval = max(MIN_METEOR_SPAWN_INTERVAL, METEOR_SPAWN_INTERVAL * METEOR_SPAWN_LEVEL_FACTOR ** (level - 1))
    area_factor = (WIDTH * HEIGHT) / (SET_WIDTH * SET_HEIGHT)
    return interval / max(MIN_AREA_FACTOR, area_factor)


def meteor_speed_factor():
    return min(MAX_METEOR_SPEED_FACTOR, 1 + METEOR_SPEED_PER_LEVEL * (level - 1))


def schedule_next_meteor():
    # The interval changes during the game, so each meteor schedules the next one
    pyglet.clock.schedule_once(spawn_meteor, meteor_spawn_interval())


def spawn_meteor(dt):
    if game_started and not game_over and not paused:
        x, y, angle = random_edge_position()
        speed = random.uniform(MIN_METEOR_SPEED, MAX_METEOR_SPEED) * meteor_speed_factor()
        vx, vy = velocity_from_angle(speed, angle)
        meteors.append(Meteor(random.choice(MET_imgs), x, y, vx, vy, batch))
    schedule_next_meteor()


def spawn_UFO(dt):
    if game_started and not game_over and not paused and level >= UFO_LEVEL:
        x, y, angle = random_edge_position()
        vx, vy = velocity_from_angle(UFO_SPEED, angle)
        ufos.append(Ufo(UFO_imgs, x, y, vx, vy, batch))


# Smaller meteor = more points (scale 1.0 gives 200, scale 0.3 about 670), rounded to tens
def calculate_points(meteor_scale):
    return int(round(POINTS * 2 / meteor_scale, -1))


def update(dt):
    global points_display_time

    if not game_started or game_over or paused:  # Do nothing if the game isn't running
        return

    ship1.update(dt)

    # Update bullets and check for collisions
    for bullet in bullets[:]:
        bullet.update(dt)
        if not bullet.sprite:
            continue

        for meteor in meteors[:]:
            if bullet.collides_with(meteor):
                points = calculate_points(meteor.sprite.scale)
                meteors.extend(meteor.split())
                bullet.delete()
                meteor.delete()
                play(SOUND_EXPLOSION)
                add_points(points)
                break

        if not bullet.sprite:
            continue

        for ufo in ufos[:]:
            if bullet.collides_with(ufo):
                bullet.delete()
                ufo.delete()
                play(SOUND_EXPLOSION)
                add_points(POINTS * 10)  # Points for destroying a UFO
                break

    # Update meteors and check for collisions with the ship
    for meteor in meteors[:]:
        meteor.update(dt)
        if ship1.can_be_hit() and meteor.collides_with(ship1):
            meteor.delete()
            lose_life()
            if game_over:
                return  # Stop immediately so the game stops updating

    # Update the UFOs and their bullets
    for ufo in ufos[:]:
        ufo.update(dt)

    for bullet in enemy_bullets[:]:
        bullet.update(dt)
        if game_over:
            return

    # Handle the points message timer
    if points_display_time > 0:
        points_display_time -= dt


# Function to export score
def export_score(player_name, score, filename=SCORES_FILE):
    path = asset(filename)
    date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Write the header only to a new or empty file
    write_header = not os.path.exists(path) or os.path.getsize(path) == 0

    with open(path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if write_header:
            writer.writerow(['Player Name', 'Score', 'Date and Time'])
        writer.writerow([player_name, score, date_time])


def get_top_scores(filename=SCORES_FILE, top_n=3):
    scores = []
    try:
        with open(asset(filename), 'r', newline='', encoding='utf-8') as file:
            for row in csv.DictReader(file):
                try:
                    scores.append((row['Player Name'], int(row['Score'])))
                except (KeyError, TypeError, ValueError):
                    continue  # Skip malformed rows
    except (FileNotFoundError, UnicodeDecodeError):
        return []

    # Sort by score in descending order and keep only the top_n entries
    return sorted(scores, key=lambda x: x[1], reverse=True)[:top_n]


top_scores = get_top_scores()


# Labels are created only once; drawing just updates their text and position
def make_label(font_size, anchor_x='center', anchor_y='center'):
    return pyglet.text.Label('', font_name=FONT, font_size=font_size,
                             anchor_x=anchor_x, anchor_y=anchor_y)


def draw_label(label, text, x, y):
    if label.text != text:
        label.text = text
    if label.x != x:
        label.x = x
    if label.y != y:
        label.y = y
    label.draw()


title_label = make_label(42)
start_label = make_label(20, anchor_y='top')
top_player_label = make_label(36)
top_score_labels = [make_label(24) for _ in range(3)]
type_name_label = make_label(24)
name_label = make_label(36)
life_lost_label = make_label(36)
continue_label = make_label(20)
game_over_label = make_label(48)
restart_label = make_label(20)
points_label = make_label(24)
paused_label = make_label(48)
unpause_label = make_label(20)
score_label = make_label(24, anchor_x='right', anchor_y='bottom')
level_label = make_label(24, anchor_x='left', anchor_y='top')
player_label = make_label(24, anchor_x='right', anchor_y='top')


@window.event
def on_draw():
    window.clear()
    background_sprite.draw()
    w, h = window.width, window.height

    if not game_started and not waiting_for_name:
        # Display the start screen
        draw_label(title_label, 'ASTEROIDS by Sophia', w // 2, h - 80)
        draw_label(start_label, 'press UP to start game', w // 2, h - 120)
        draw_label(top_player_label, 'TOP PLAYERS OF ALL TIMES', w // 2, h // 2 + 20)
        for index, (name, points) in enumerate(top_scores):
            draw_label(top_score_labels[index], f'{index + 1}. {name}: {points}',
                       w // 2, h // 2 - 100 - index * 30)
        return

    if waiting_for_name:
        draw_label(type_name_label, 'Enter your name and press ENTER:', w // 2, h // 2)
        draw_label(name_label, player_name_input, w // 2, h // 2 - 60)
        return

    if game_over:
        draw_label(game_over_label, 'GAME OVER', w // 2, h // 2)
        draw_label(restart_label, 'press ENTER to restart the game', w // 2, h // 2 - 80)
    else:
        batch.draw()
        if life_lost:
            draw_label(life_lost_label, LOST_LIFE_TEXT, w // 2, h // 2)
            draw_label(continue_label, 'press UP to continue', w // 2, h // 2 - 80)
        if points_display_time > 0:
            draw_label(points_label, points_text, w // 2, h // 4)
        if paused:
            draw_label(paused_label, 'PAUSED', w // 2, h // 2)
            draw_label(unpause_label, 'press P or ESC to continue', w // 2, h // 2 - 80)

    # Score bottom right, level top left, player name top right
    draw_label(score_label, f'Score: {score}', w - 20, 20)
    draw_label(level_label, f'Difficulty: {level}', 20, h - 20)
    draw_label(player_label, f'Player: {player_name}', w - 20, h - 20)


@window.event
def on_text(text):
    global player_name_input
    if waiting_for_name:
        # Only printable characters (no Enter etc.) and a limited name length
        text = ''.join(ch for ch in text if ch.isprintable())
        player_name_input = (player_name_input + text)[:MAX_NAME_LENGTH]


def shoot():
    if game_started and not game_over and not life_lost and not paused and ship1.alive:
        bullets.append(Bullet(BULLET_imgs, ship1.sprite.x, ship1.sprite.y, ship1.sprite.rotation, batch))
        play(SOUND_LASER)


@window.event
def on_key_press(symbol, modifiers):
    global game_started, waiting_for_name, player_name, player_name_input, paused

    # The new size is picked up in on_resize
    if symbol == key.F11:
        window.set_fullscreen(not window.fullscreen)  # toggle fullscreen
    elif symbol == key.F10 and window.fullscreen:
        window.set_fullscreen(False)

    if not game_started and not waiting_for_name:
        if symbol == key.UP:
            waiting_for_name = True  # Start waiting for the player's name
    elif not game_started and waiting_for_name:
        if symbol == key.BACKSPACE:
            player_name_input = player_name_input[:-1]
        elif symbol == key.ENTER:
            player_name = player_name_input.strip() or 'Player'
            waiting_for_name = False
            reset_game()
    elif game_over:
        if symbol == key.ENTER:
            reset_game()  # Full game restart after "Game Over"
    elif symbol in PAUSE_KEYS:
        paused = not paused
        return pyglet.event.EVENT_HANDLED  # Stop ESC from closing the window
    elif paused:
        pass  # Ship controls don't work while paused
    elif life_lost:
        if symbol == key.UP:
            restart_after_life_lost()  # Restart only after losing a life
    else:
        if symbol == key.A or symbol == key.LEFT:
            ship1.keys['left'] = True
        elif symbol == key.D or symbol == key.RIGHT:
            ship1.keys['right'] = True
        elif symbol == key.W or symbol == key.UP:
            ship1.keys['up'] = True
        elif symbol == key.S or symbol == key.DOWN:
            ship1.keys['down'] = True
        elif symbol == key.SPACE:  # Space key to shoot
            shoot()


@window.event
def on_mouse_press(x, y, button, modifiers):
    if button == mouse.LEFT:
        shoot()


@window.event
def on_key_release(symbol, modifiers):
    if game_started and not game_over and ship1 is not None:
        if symbol == key.A or symbol == key.LEFT:
            ship1.keys['left'] = False
        elif symbol == key.D or symbol == key.RIGHT:
            ship1.keys['right'] = False
        elif symbol == key.W or symbol == key.UP:
            ship1.keys['up'] = False
        elif symbol == key.S or symbol == key.DOWN:
            ship1.keys['down'] = False


@window.event
def on_deactivate():
    # Pause automatically when the player switches to another window
    global paused
    if game_started and not game_over:
        paused = True


@window.event
def on_resize(width, height):
    global WIDTH, HEIGHT
    # Fullscreen, maximize and dragging the window edge all end up here
    WIDTH, HEIGHT = width, height
    update_background()


update_background()
create_ship()
create_life_sprites()

# Running the app
if __name__ == '__main__':
    pyglet.app.run()
