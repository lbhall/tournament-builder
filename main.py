import json
import math
import random
import curses
import logging
from typing import Optional

logging.basicConfig(filename='tournament.log', level=logging.INFO)
logging.info('started')

MAX_PLAYERS = 32
WINNER_SIDE = 'W'
LOSER_SIDE = 'L'

loser_configuration = {
    '2': {
        'number_of_rounds': 0,
    },
    '4': {
        'number_of_rounds': 2,
        'matches_per_round': {
            '1': 1,
            '2': 1,
        }
    },
    '8': {
        'number_of_rounds': 4,
        'matches_per_round': {
            '1': 2,
            '2': 2,
            '3': 1,
            '4': 1,
        }
    },
    '16': {
        'number_of_rounds': 6,
        'matches_per_round': {
            '1': 4,
            '2': 4,
            '3': 2,
            '4': 2,
            '5': 1,
            '6': 1,
        }
    },
    '32': {
        'number_of_rounds': 8,
        'matches_per_round': {
            '1': 8,
            '2': 8,
            '3': 4,
            '4': 4,
            '5': 2,
            '6': 2,
            '7': 1,
            '8': 1,
        }
    },
    '64': {
        'number_of_rounds': 10,
        'matches_per_round': {
            '1': 16,
            '2': 16,
            '3': 8,
            '4': 8,
            '5': 4,
            '6': 4,
            '7': 2,
            '8': 2,
            '9': 1,
            '10': 1,
        }
    },
}


stdscr = None


def initialize_curses():
    # BEGIN ncurses startup/initialization...
    # Initialize the curses object.
    global stdscr
    stdscr = curses.initscr()

    # Do not echo keys back to the client.
    curses.noecho()

    # Non-blocking or cbreak mode... do not wait for Enter key to be pressed.
    curses.cbreak()

    # Turn off blinking cursor
    curses.curs_set(False)

    # Enable color if we can...
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
    # Optional - Enable the keypad. This also decodes multi-byte key sequences
    # stdscr.keypad(True)


caughtExceptions = ""


def run_curses():
    global stdscr
    global caughtExceptions

    try:
        # Coordinates start from top left, in the format of y, x.
        stdscr.addstr(0, 0, "Hello, world!")
        screenDetailText = "This screen is [" + str(curses.LINES) + "] high and [" + str(curses.COLS) + "] across."
        startingXPos = int((curses.COLS - len(screenDetailText)) / 2)
        stdscr.addstr(3, startingXPos, screenDetailText)
        stdscr.addstr(5, curses.COLS - len("Press a key to quit."), "Press a key to quit.")

        # Actually draws the text above to the positions specified.
        stdscr.refresh()

        # Grabs a value from the keyboard without Enter having to be pressed (see cbreak above)
        stdscr.getch()
    except Exception as err:
        # Just printing from here will not work, as the program is still set to
        # use ncurses.
        # print ("Some error [" + str(err) + "] occurred.")
        logging.exception(f'Exception: {err}')


def shutdown_curses():
    # BEGIN ncurses shutdown/deinitialization...
    # Turn off cbreak mode...
    curses.nocbreak()

    # Turn echo back on.
    curses.echo()

    # Restore cursor blinking.
    curses.curs_set(True)

    # Turn off the keypad...
    # stdscr.keypad(False)

    # Restore Terminal to original state.
    curses.endwin()

    # END ncurses shutdown/deinitialization...


with open("players.json", "r") as file:
    data = json.load(file)

available_players = data["players"]


class Tournament:
    double_elimination = False
    bracket_size = None
    tournament_bracket = {
        WINNER_SIDE: {},
        LOSER_SIDE: {}
    }
    number_of_players = 0
    max_winner_round = 0
    max_loser_round = 0

    def __init__(self, num_players, double_elimination=False):
        self.number_of_players = num_players
        self.double_elimination = False if num_players <= 2 else double_elimination
        self.set_bracket_size()
        logging.info(f'Init Tournament-> Num Players: {self.number_of_players}, Bracket Size: {self.bracket_size}, Double Elimination: {self.double_elimination}')

    def get_max_round(self, bracket_side='W'):
        return list(self.tournament_bracket[bracket_side].keys())[-1]

    def find_last_winner_match_ref(self):
        try:
            return self.tournament_bracket[WINNER_SIDE][self.get_max_round()][0]
        except Exception as err:
            logging.exception(f'Exception: {err}')

        return ''

    def find_match(self, match_ref) -> Optional["Match"]:
        try:
            if match_ref == 'FINALS':
                return self.find_last_winner_match_ref()

            parts = match_ref.split(':')
            tournament_round = parts[0][1]
            match_in_round = parts[1]
            winner_or_loser = match_ref[0]

            return self.tournament_bracket[winner_or_loser][int(tournament_round)][int(match_in_round) - 1]
        except Exception as err:
            logging.exception(f'Exception: {err}, match not found for match: {match_ref}')

        return None

    @staticmethod
    def get_loser_round(tournament_round):
        match tournament_round:
            case 1:
                return 1
            case 2:
                return 2
            case 3:
                return 4
            case 4:
                return 6
            case 5:
                return 8

    def set_bracket_size(self):
        self.bracket_size = 0
        power_of_2 = 0
        while self.bracket_size < self.number_of_players:
            power_of_2 += 1
            self.bracket_size = pow(2, power_of_2)

    def map_from(self, from_ref, to_ref):
        match = self.find_match(to_ref)
        if match is not None:
            if match.player1_from is None:
                match.player1_from = from_ref
            else:
                match.player2_from = from_ref

    def process_mapping(self, bracket_side):
        for i in range(1, self.get_max_round(bracket_side)):
            current_round_matches = self.tournament_bracket[bracket_side][i]
            for match in current_round_matches:
                self.map_from(match.match_reference(), match.winner_match)
                if match.loser_match is not None:
                    self.map_from(match.match_reference(), match.loser_match)

    def create_from_mappings(self):
        self.process_mapping(WINNER_SIDE)
        self.process_mapping(LOSER_SIDE)

    def generate_bracket(self):
        tournament_round = 1
        num_matches_in_round = self.bracket_size / 2
        not_done = True
        backwards=False
        populate_loser_match_fully = True

        # generate winner side draw
        while not_done:
            if num_matches_in_round == 1:
                not_done = False

            self.tournament_bracket[WINNER_SIDE][tournament_round] = (
                self.generate_winner_round(
                    tournament_round, num_matches_in_round, backwards, populate_loser_match_fully))
            tournament_round += 1
            num_matches_in_round = num_matches_in_round / 2
            backwards = not backwards
            populate_loser_match_fully = False

        self.max_winner_round = tournament_round

        if self.double_elimination:
            new_match = Match(False, tournament_round, 1)
            self.tournament_bracket[WINNER_SIDE][tournament_round] = [new_match]

            # generate the loser side draw
            for loser_round in range(loser_configuration[str(self.bracket_size)]['number_of_rounds']):
                tournament_round = loser_round + 1
                self.tournament_bracket[LOSER_SIDE][tournament_round] = self.generate_loser_round(tournament_round)
                self.max_loser_round = tournament_round
        self.create_from_mappings()

    def generate_winner_round(
            self, tournament_round, num_matches_in_round, backwards=False, populate_loser_match_fully=True):
        round_matches = []

        for match_in_round in range(int(num_matches_in_round)):
            new_match = Match(False, tournament_round, match_in_round + 1)
            if num_matches_in_round > 1 or num_matches_in_round == 1 and self.double_elimination:
                winner_match_in_round = int(math.ceil(new_match.match_in_round / 2))
                winner_reference = WINNER_SIDE + str(tournament_round + 1) + ':' + str(winner_match_in_round)
                new_match.winner_match = winner_reference
                if self.double_elimination:
                    loser_round = Tournament.get_loser_round(tournament_round)
                    if not backwards:
                        if populate_loser_match_fully:
                            loser_match_in_round = winner_match_in_round
                        else:
                            loser_match_in_round = match_in_round + 1
                    else:
                        loser_match_in_round = int(num_matches_in_round - match_in_round)
                    loser_reference = LOSER_SIDE + str(loser_round) + ':' + str(loser_match_in_round)
                    new_match.loser_match = loser_reference
            round_matches.append(new_match)
        return round_matches

    def generate_loser_round(self, loser_bracket_round):
        matches_in_round = loser_configuration[str(self.bracket_size)]['matches_per_round'][str(loser_bracket_round)]
        round_matches = []
        even = False
        if loser_bracket_round // 2 * 2 == loser_bracket_round:
            even = True

        last_match = None
        for match_in_round in range(matches_in_round):
            new_match = Match(True, loser_bracket_round, match_in_round + 1)
            last_match = new_match
            if loser_bracket_round < loser_configuration[str(self.bracket_size)]['number_of_rounds']:
                target_match_in_next_round = match_in_round
                if even:
                    target_match_in_next_round = math.ceil(match_in_round/2)
                target_match_in_next_round += 1
                new_match.winner_match = f'L{loser_bracket_round + 1}:{target_match_in_next_round}'
            round_matches.append(new_match)

        if last_match is not None:
            finals_ref = self.find_last_winner_match_ref()
            last_match.winner_match = finals_ref

        return round_matches

    def tourney_type(self):
        return 'Double' if self.double_elimination else 'Single'


class Match:
    player1 = None
    player1_from = None
    player2 = None
    player2_from = None
    winner = None
    winner_match = None
    loser_side = False
    loser_match = None
    tournament_round = 0
    match_in_round = 0

    def __init__(self, loser_side, tournament_round, match_in_round):
        self.loser_side = loser_side
        self.tournament_round = tournament_round
        self.match_in_round = match_in_round

    def player_str(self, player1=True):
        player_from = ''

        if player1:
            player_name = self.player1 if self.player1 is not None else 'None'
            if self.player1_from is not None:
                player_from = self.player1_from
        else:
            player_name = self.player2 if self.player2 is not None else 'None'
            if self.player2_from is not None:
                player_from = self.player2_from

        if len(player_from) > 0:
            player_from = f'({player_from})'
        return f'{player_name}{player_from}'

    def __repr__(self):
        match_reference = self.match_reference()
        string_val = f'<Match {match_reference} {self.player_str(True)} vs {self.player_str(False)}'
        if self.winner_match is not None:
            string_val += f' W={self.winner_match}'
        if self.loser_match is not None:
            string_val += f' L={self.loser_match}'
        string_val += '>'
        return string_val

    def __str__(self):
        match_reference = self.match_reference()
        string_val = f'{match_reference} {self.player_str(True)} vs {self.player_str(False)}'
        if self.winner_match is not None:
            string_val += f' W={self.winner_match}'
        if self.loser_match is not None:
            string_val += f' L={self.loser_match}'
        return string_val

    def match_reference(self):
        winner_or_loser = WINNER_SIDE if not self.loser_side else LOSER_SIDE
        return f'{winner_or_loser}{self.tournament_round}:{self.match_in_round}'


class ManageTourney:
    tournament = None

    def __init__(self, tournament):
        self.tournament = tournament

    def tournament_title(self, stdscr):

        title = (f'{self.tournament.number_of_players} Players in tournament / '
                 f'{self.tournament.bracket_size} Players Bracket / {self.tournament.tourney_type()} Elimination')
        stdscr.attron(curses.color_pair(2))
        stdscr.attron(curses.A_BOLD)
        stdscr.addstr(0, 0, title)
        stdscr.attroff(curses.color_pair(2))
        stdscr.attroff(curses.A_BOLD)

        return

    def print_tournament_bracket(self):
        print(self.tournament_title())
        print()

        print('Winner Side')
        for key in self.tournament.tournament_bracket[WINNER_SIDE]:
            print(f'Round {key}')
            for match in self.tournament.tournament_bracket[WINNER_SIDE][key]:
                print(match)
            print()

        print('Loser Side')
        for key in self.tournament.tournament_bracket[LOSER_SIDE]:
            print(f'Round {key}')
            for match in self.tournament.tournament_bracket[LOSER_SIDE][key]:
                print(match)
            print()

    @staticmethod
    def bracket_text(stdscr, show_winners):
        bracket_text = 'Winners' if show_winners else 'Losers'
        stdscr.addstr(2, 0, f'{bracket_text} Bracket')

    @staticmethod
    def menu(stdscr):
        stdscr.attron(curses.color_pair(1))
        stdscr.attron(curses.A_BOLD)
        stdscr.addstr(curses.LINES-1, 0, "(W)inner (L)oser (R)egenerate (A)ssign (U)nassign (Q)uit")
        stdscr.attroff(curses.color_pair(1))
        stdscr.attroff(curses.A_BOLD)

    @staticmethod
    def get_current_line_for_winner_by_round(current_round, bracket_side):
        match current_round:
            case 1:
                return 5
            case 2:
                if bracket_side == WINNER_SIDE:
                    return 6
                else:
                    return 5
            case 3:
                if bracket_side == WINNER_SIDE:
                    return 8
                else:
                    return 7
            case 4:
                if bracket_side == WINNER_SIDE:
                    return 13
                else:
                    return 7
            case 5:
                if bracket_side == WINNER_SIDE:
                    return 22
                else:
                    return 7
            case 6:
                if bracket_side == WINNER_SIDE:
                    return 14
                else:
                    return 7
            case _:
                return 3

    def print_tournament_winner_bracket(self, stdscr):
        current_column = 0
        last_match_printed = 0
        for key in self.tournament.tournament_bracket[WINNER_SIDE]:
            previous_key = int(key) - 1
            matches_printed = 0
            current_line = ManageTourney.get_current_line_for_winner_by_round(int(key), WINNER_SIDE)
            stdscr.addstr(3, current_column, f'Round {key}')

            for match in self.tournament.tournament_bracket[WINNER_SIDE][key]:
                if matches_printed == 2 and int(key) == 1:
                    matches_printed = 0
                    current_line += 1
                if int(key) == 2 and matches_printed > 0:
                    current_line += 3
                if int(key) == 3 and matches_printed > 0:
                    current_line += 8
                if int(key) == 4 and matches_printed > 0:
                    current_line += 18

                if previous_key > 0 and len(self.tournament.tournament_bracket[WINNER_SIDE][previous_key]) == 1:
                    current_line = last_match_printed
                stdscr.addstr(current_line, current_column, str(match))
                last_match_printed = current_line
                current_line += 2
                matches_printed += 1
            current_column += 50

    def print_tournament_loser_bracket(self, stdscr):
        current_column = 0
        last_match_printed = 0
        for key in self.tournament.tournament_bracket[LOSER_SIDE]:
            previous_key = int(key) - 1
            matches_printed = 0
            current_line = 0
            stdscr.addstr(3, current_column, f'Round {key}')

            for match in self.tournament.tournament_bracket[LOSER_SIDE][key]:
                match key:
                    case 1:
                        if matches_printed == 0:
                            current_line = 5
                        if matches_printed > 0:
                            current_line += 1
                    case 2:
                        if matches_printed == 0:
                            current_line = 5
                        elif matches_printed > 0:
                            current_line += 1
                    case 3:
                        if matches_printed == 0:
                            current_line = 6
                        elif self.tournament.bracket_size == 32 and matches_printed > 0:
                            current_line += 3
                        else:
                            current_line += 3
                    case 4:
                        if matches_printed == 0:
                            current_line = 6
                        elif self.tournament.bracket_size == 32 and matches_printed > 0:
                            current_line += 3
                        else:
                            current_line += 3
                    case 5:
                        if self.tournament.bracket_size == 32 and matches_printed > 0:
                            current_line += 7
                        elif self.tournament.bracket_size == 32 and matches_printed == 0:
                            current_line = 8
                        elif self.tournament.bracket_size == 16 and matches_printed == 0:
                            current_line = 8
                        elif self.tournament.bracket_size == 32 and matches_printed == 0:
                            current_line = 14
                        elif self.tournament.bracket_size == 32 and matches_printed > 0:
                            current_line += 9
                        elif matches_printed == 0:
                            current_line = 6
                        else:
                            current_line += 4
                    case 6:
                        if self.tournament.bracket_size == 16 and matches_printed > 0:
                            current_line = 9
                        elif self.tournament.bracket_size == 32 and matches_printed > 0:
                            current_line += 7
                        elif self.tournament.bracket_size == 32 and matches_printed == 0:
                            current_line += 8
                        elif matches_printed == 0:
                            current_line = 7
                        else:
                            current_line += 4

                    case 7:
                        if matches_printed == 0:
                            match self.tournament.bracket_size:
                                case 32:
                                    current_line = 12
                                case _:
                                    current_line = 7
                        else:
                            match self.tournament.bracket_size:
                                case 32:
                                    current_line += 7
                                case _:
                                    current_line += 4
                    case 8:
                        if matches_printed == 0:
                            match self.tournament.bracket_size:
                                case 32:
                                    current_line = 12
                                case _:
                                    current_line = 7
                        else:
                            match self.tournament.bracket_size:
                                case 32:
                                    current_line += 7
                                case _:
                                    current_line += 4
                if previous_key > 0 and len(self.tournament.tournament_bracket[LOSER_SIDE][previous_key]) == 1:
                    current_line = last_match_printed
                stdscr.addstr(current_line, current_column, str(match))
                last_match_printed = current_line
                current_line += 1
                matches_printed += 1
            current_column += 40

    def print_tournament_bracket_with_curses(self, stdscr, show_winners=True):
        self.tournament_title(stdscr)

        if show_winners:
            ManageTourney.bracket_text(stdscr, True)
            self.print_tournament_winner_bracket(stdscr)
        else:
            ManageTourney.bracket_text(stdscr, False)
            self.print_tournament_loser_bracket(stdscr)

        ManageTourney.menu(stdscr)
        stdscr.refresh()


active_tournament = None
worker = None
players_list = []


def generate_randomized_players():
    for i in range(NUMBER_OF_PLAYERS_FOR_TOURNAMENT):
        random_player = random.choice(available_players)
        players_list.append(random_player)
        available_players.remove(random_player)


def initialize_tourney():
    global active_tournament
    global worker
    global NUMBER_OF_PLAYERS_FOR_TOURNAMENT

    NUMBER_OF_PLAYERS_FOR_TOURNAMENT = 0
    while NUMBER_OF_PLAYERS_FOR_TOURNAMENT < 4:
        NUMBER_OF_PLAYERS_FOR_TOURNAMENT = random.randint(1, MAX_PLAYERS)
    active_tournament = Tournament(NUMBER_OF_PLAYERS_FOR_TOURNAMENT, True)
    active_tournament.generate_bracket()
    worker = ManageTourney(active_tournament)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    try:
        initialize_curses()
        initialize_tourney()
        if worker is not None:
            c = None
            show_winners = True
            while c != ord('q'):
                try:
                    worker.print_tournament_bracket_with_curses(stdscr, show_winners)
                    c = stdscr.getch()
                    if c == ord('l'):
                        show_winners = False
                    if c == ord('w'):
                        show_winners = True
                    if c == ord('r'):
                        initialize_tourney()
                    if c == ord('a'):
                        generate_randomized_players()
                    stdscr.clear()
                except Exception as err:
                    logging.exception(f'Exception: {err}')

            # tournament.print_tournament_bracket()
            # run_curses()
    except Exception as err:
        logging.exception(f'Exception: {err}')
    finally:
        shutdown_curses()
