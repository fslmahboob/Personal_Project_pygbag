import asyncio
import os
import pygame
import random
import sys

# set the working directory to the same as the script's directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

"""SETTINGS"""
# Display Settings
DEFAULT_IMAGE_SIZE = (300, 300)
FPS = 120
HEIGHT = 1000
WIDTH = 1600
START_X, START_Y = 0, -300
X_OFFSET, Y_OFFSET = 20, 0 # 1600 pixels divided by 5 reels -> 20 pixels remain

# Images
BG_IMAGE_PATH = 'img/bg1.png'
GAME_INDICES = [1, 2, 3] # 0 and 4 are outside of play area

# Text
TEXT_COLOR = 'GREEN'
UI_FONT = 'sfx/Allura-Regular.ttf'
UI_FONT_SIZE = 30
WIN_FONT_SIZE = 110

# Symbols in a dictionary
# symbols = {
#     'dollar': 'img/0_dollar.png',
#     'floppy': 'img/0_floppy.png',
#     'hourglass': 'img/0_hourglass.png',
#     'seven': 'img/0_seven.png',
#     'telephone': 'img/0_telephone.png'
# }

symbols = {
    'cutiepie': 'img/0_cutiepie.png',
    'floppy': 'img/0_kiss.png',
    'hourglass': 'img/0_heart.png',
    'seven': 'img/0_us.png',
    'telephone': 'img/0_cake.png'
}

class Game:
    def __init__(self):

        # General Setup
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Slot Machine Game')
        self.clock = pygame.time.Clock()
        self.bg_image = pygame.image.load(BG_IMAGE_PATH)

        self.machine = Machine()
        self.delta_time = 0

        # Sound
        main_sound = pygame.mixer.Sound('sfx/track.ogg')
        main_sound.play(loops = -1) # play the music continuously in the background

    def run(self):
        self.start_time = pygame.time.get_ticks() # tells us when the game starts

        while True:
            # Handle quit operation
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            # Time Variables - runs everytime the while statement is True
            self.delta_time = (pygame.time.get_ticks() - self.start_time) / 1000
            self.start_time = pygame.time.get_ticks()

            pygame.display.update()

            # Draw background image
            self.screen.blit(self.bg_image, (0, 0))

            # Feed delta time variable into instance of Machine Class
            self.machine.update(self.delta_time)
            self.clock.tick(FPS)

"""The Slot Machine"""

class Machine:
    def __init__(self):
        self.display_surface = pygame.display.get_surface()
        self.machine_balance = 10000.00
        self.reel_index = 0
        self.reel_list = {}
        self.can_toggle = True
        self.spinning = False

        # Results
        self.prev_result = {0: None, 1: None, 2: None, 3: None, 4: None}
        self.spin_result = {0: None, 1: None, 2: None, 3: None, 4: None}

        # Calling this method to cause the symbol images to move
        self.spawn_reels()
        # Create player object
        self.currPlayer = Player()
        # Pass player object into UI class
        self.ui = UI(self.currPlayer)

        # Import Sound
        self.win_three = pygame.mixer.Sound('sfx/winthree.ogg')
        self.win_three.set_volume(0.6)

    def cooldowns(self):
        # Only lets player spin if all reels are NOT spinning
        for reel in self.reel_list:
            if self.reel_list[reel].reel_is_spinning:
                self.can_toggle = False
                self.spinning = True

        # Change current value of self.can_toggle and check negative case of self.can_toggle -> reel is spinning
        if not self.can_toggle and [self.reel_list[reel].reel_is_spinning for reel in self.reel_list].count(False) == 5:
            self.can_toggle = True
            self.spin_result = self.get_result()

            if self.check_wins(self.spin_result):
                self.win_data = self.check_wins(self.spin_result)
                #Play the win sound
                self.play_win_sound(self.win_data)
                self.pay_player(self.win_data, self.currPlayer)

    def input(self):
        keys = pygame.key.get_pressed()

        # Checks for space key, ability to goggle spin and balance to cover bet size
        # Checks for space key, ability to toggle spin and balance to cover bet size
        if keys[pygame.K_SPACE] and self.can_toggle and self.currPlayer.balance >= self.currPlayer.bet_size:
            self.toggle_spinning()
            self.spin_time = pygame.time.get_ticks()
            self.currPlayer.place_bet()
            self.machine_balance += self.currPlayer.bet_size
            #print(self.currPlayer.get_data()) #for testing purposes if player data is getting updated correctly
            self.currPlayer.last_payout = None

    def draw_reels(self, delta_time):
        for reel in self.reel_list:
            self.reel_list[reel].animate(delta_time)

    def spawn_reels(self):
        # check if self.reel has anything in it
        if not self.reel_list:
            x_topleft, y_topleft = 10, -300
        while self.reel_index < 5:
            if self.reel_index > 0:
                x_topleft, y_topleft = x_topleft + (300 + X_OFFSET), y_topleft

            # key is going to be value of reel_index which instantiates reel object
            self.reel_list[self.reel_index] = Reel((x_topleft, y_topleft)) # need to create reel class
            self.reel_index += 1

    def toggle_spinning(self):
        if self.can_toggle:
            self.spin_time = pygame.time.get_ticks()
            self.spinning = not self.spinning
            self.can_toggle = False

            for reel in self.reel_list:
                self.reel_list[reel].start_spin(int(reel)*200) # 200 seconds delay for each spin

    def get_result(self):
        for reel in self.reel_list:
            self.spin_result[reel] = self.reel_list[reel].reel_spin_result()
        return self.spin_result

    def check_wins(self, result):
        hits = {}
        horizontal = flip_horizontal(result)
        for row in horizontal:
            for sym in row:
                if row.count(sym) > 2: # Potential win
                    possible_win = [idx for idx, val in enumerate(row) if sym == val] # will result in a list of indices

                    # Check for possible win sequence > 2, then add to hits
                    if len(longest_seq(possible_win)) > 2:
                        hits[horizontal.index(row) + 1] = [sym, longest_seq(possible_win)]
        if hits:
            return hits

    def pay_player(self, win_data, curr_player):
        multiplier = 0
        spin_payout = 0

        for v in win_data.values():
            multiplier += len(v[1])
        spin_payout = (multiplier * curr_player.bet_size)
        curr_player.balance += spin_payout
        self.machine_balance -= spin_payout
        curr_player.last_payout = spin_payout
        curr_player.total_won += spin_payout

    def play_win_sound(self, win_data):
        sum = 0
        for item in win_data.values():
            sum += len(item[1])
        if sum >= 3: self.win_three.play()

    def update(self, delta_time):
        self.cooldowns()
        self.input()
        self.draw_reels(delta_time)
        for reel in self.reel_list:
            self.reel_list[reel].symbol_list.draw(self.display_surface)
            self.reel_list[reel].symbol_list.update()
        self.ui.update()

"""Creating the  animations for the Reels"""
class Reel:
    def __init__(self, pos):
        # keep track of symbols in a list using Sprite group
        self.symbol_list = pygame.sprite.Group()
        # create an initial shuffled list of symbols
        self.shuffled_keys = list(symbols.keys())
        random.shuffle(self.shuffled_keys)
        self.shuffled_keys = self.shuffled_keys[:5] # only matters when there are more than 5 symbols

        self.reel_is_spinning = False

        # Sounds
        self.stop_sound = pygame.mixer.Sound('sfx/stop.ogg')
        self.stop_sound.set_volume(0.5)

        for idx, item in enumerate(self.shuffled_keys):
            self.symbol_list.add(Symbol(symbols[item], pos, idx))
            pos = list(pos)
            pos[1] += 300
            pos = tuple(pos)

    def animate(self, delta_time): # check if wheel is spinning
        # everytime this function is called, time is subtracted from delay_time and spin_time
        # this determines whether we are spinning or stopping
        if self.reel_is_spinning:
            self.delay_time -= (delta_time * 1000)
            self.spin_time -= (delta_time * 1000)
            reel_is_stopping = False

            if self.spin_time < 0:
                reel_is_stopping = True

            # Stagger real spin start animation
            if self.delay_time <= 0:

                # Iterate through all 5 symbols in real; truncate; add new random symbol on top of stack
                for symbol in self.symbol_list:
                    symbol.rect.bottom += 100 # make the symbols move down 100 pixels

                    # Correct spacing -> depends on addition above hitting 1200
                    if symbol.rect.top == 1200:
                        if reel_is_stopping:
                            self.reel_is_spinning = False
                            self.stop_sound.play()

                        symbol_idx = symbol.idx
                        symbol.kill()
                        # Spawn random symbol in place of the above
                        self.symbol_list.add(Symbol(symbols[random.choice(self.shuffled_keys)], ((symbol.x_val), -300), symbol_idx))
    def start_spin(self, delay_time):
        self.delay_time = delay_time
        self.spin_time = 1000 + delay_time
        self.reel_is_spinning = True

    def reel_spin_result(self):
        # Get and return text representation of symbols in a given reel
        spin_symbols = []
        for i in GAME_INDICES:
            spin_symbols.append(self.symbol_list.sprites()[i].sym_type)
        return spin_symbols[::-1] # return backwards
class Symbol(pygame.sprite.Sprite):
    def __init__(self, pathToFile, pos, idx):
        super().__init__()

        # Friendly name
        self.sym_type = pathToFile.split('/')[1].split('.')[0]

        self.pos = pos
        self.idx = idx
        self.image = pygame.image.load(pathToFile).convert_alpha()
        self.rect = self.image.get_rect(topleft = pos)
        self.x_val = self.rect.left

    def update(self):
        pass

"""Creating the UI showing player stats and wins"""
class UI:
    def __init__(self, player):
        self.player = player
        self.display_surface = pygame.display.get_surface()
        self.font, self.bet_font = pygame.font.Font(UI_FONT, UI_FONT_SIZE), pygame.font.Font(UI_FONT, UI_FONT_SIZE)
        self.win_font = pygame.font.Font(UI_FONT, WIN_FONT_SIZE)
        self.win_text_angle = random.randint(-4, 4)

    def display_info(self):
        player_data = self.player.get_data()

        # Balance and bet size
        balance_surf = self.font.render("Balance: $" + player_data['balance'], True, TEXT_COLOR, None)
        x, y = 20, self.display_surface.get_size()[1] - 30
        balance_rect = balance_surf.get_rect(bottomleft = (x, y))

        bet_surf = self.bet_font.render("Wager: $" + player_data['bet_size'], True, TEXT_COLOR, None)
        x = self.display_surface.get_size()[0] - 20
        bet_rect = bet_surf.get_rect(bottomright = (x, y))

        # Draw player data
        pygame.draw.rect(self.display_surface, False, balance_rect)
        pygame.draw.rect(self.display_surface, False, bet_rect)
        self.display_surface.blit(balance_surf, balance_rect)
        self.display_surface.blit(bet_surf, bet_rect)

        # Print last win if applicable
        if self.player.last_payout:
            last_payout = player_data['last_payout']
            win_surf = self.win_font.render("WIN! $" + last_payout, True, TEXT_COLOR, None)
            x1 = 800
            y1 = self.display_surface.get_size()[1] - 60
            win_surf = pygame.transform.rotate(win_surf, self.win_text_angle)
            win_rect = win_surf.get_rect(center = (x1, y1))
            self.display_surface.blit(win_surf, win_rect)

    def update(self):
        pygame.draw.rect(self.display_surface, 'Black', pygame.Rect(0, 900, 1600, 100))
        self.display_info()

"""Player Data"""
class Player():
    def __init__(self):
        self.balance = 1000.00
        self.bet_size = 10.00
        self.last_payout = 0.00
        self.total_won = 0.00
        self.total_wager = 0.00

    def get_data(self):
        player_data = {}
        player_data['balance'] = "{:.2f}".format(self.balance)
        player_data['bet_size'] = "{:.2f}".format(self.bet_size)
        player_data['last_payout'] = "{:.2f}".format(self.last_payout) if self.last_payout else "N/A"
        player_data['total_won'] = "{:.2f}".format(self.total_won)
        player_data['total_wager'] = "{:.2f}".format(self.total_wager)
        return player_data

    def place_bet(self):
        bet = self.bet_size
        self.balance -= bet
        self.total_wager += bet

"""Helper functions to detect wins"""
def flip_horizontal(result):
    # Flip results horizontally to keep them in a more readable list
    horizontal_values = []
    # loop through the values in the dict
    for value in result.values():
        horizontal_values.append(value)
    # Rotate 90 degrees to get text representation of spin in order
    rows, cols = len(horizontal_values), len(horizontal_values[0])
    hvals2 = [[""] * rows for _ in range(cols)]
    for x in range(rows):
        for y in range(cols):
            hvals2[y][rows - x - 1] = horizontal_values[x][y]
    hvals3 = [item[::-1] for item in hvals2]
    return hvals3

# keeping track of a list of hits which is the row
def longest_seq(hit):
    subSeqLength, longest = 1, 1
    start, end = 0, 0
    for i in range(len(hit) - 1):
        if hit[i] == hit[i + 1] - 1:
            subSeqLength += 1
            if subSeqLength > longest:
                longest = subSeqLength
                start = i + 2 - subSeqLength
                end = i + 2
        else:
            subSeqLength = 1
    return hit[start:end]

if __name__ == '__main__':
    async def main():
        # My game loop
        game = Game()
        game.run()
        #await asyncio.sleep(0)
        pygame.display.update(), await asyncio.sleep(0)
    asyncio.run(main())