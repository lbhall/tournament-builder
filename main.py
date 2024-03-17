import json
import math
import random

MAX_PLAYERS = 64
NUMBER_OF_PLAYERS_FOR_TOURNAMENT = random.randint(1, MAX_PLAYERS)
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


def find_match(tournament_bracket, match_ref):
    if match_ref == 'FINALS':
        winner_rounds = tournament_bracket[WINNER_SIDE].keys()
        if len(winner_rounds) > 0:
            last_round = winner_rounds[-1]
            return tournament_bracket[WINNER_SIDE][last_round][0]

    parts = match_ref.split(':')
    tournament_round = parts[0][1]
    match_in_round = parts[1]
    winner_or_loser = match_ref[0]

    bracket = tournament_bracket[winner_or_loser]
    return bracket[tournament_round][match_in_round-1]


with open("players.json", "r") as file:
    data = json.load(file)

available_players = data["players"]

players_list = []
for i in range(NUMBER_OF_PLAYERS_FOR_TOURNAMENT):
    random_player = random.choice(available_players)
    players_list.append(random_player)
    available_players.remove(random_player)


class Tournament:
    double_elimination = False
    bracket_size = None
    tournament_bracket = {
        WINNER_SIDE: {},
        LOSER_SIDE: {}
    }
    number_of_players = 0

    def __init__(self, num_players, double_elimination=False):
        self.number_of_players = num_players
        self.double_elimination = False if num_players <= 2 else double_elimination
        self.set_bracket_size()

    def get_loser_round(self, tournament_round):
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
        power_of_2 = 0
        while self.bracket_size < self.number_of_players:
            power_of_2 += 1
            self.bracket_size = pow(2, power_of_2)

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

        if self.double_elimination:
            new_match = Match(False, tournament_round, 1)
            self.tournament_bracket[WINNER_SIDE][tournament_round] = [new_match]

        # generate the loser side draw
        for loser_round in range(loser_configuration[str(self.bracket_size)]['number_of_rounds']):
            tournament_round = loser_round + 1
            self.tournament_bracket[LOSER_SIDE][tournament_round] = self.generate_loser_round(tournament_round)

    def generate_winner_round(
            self, tournament_round, num_matches_in_round, backwards=False, populate_loser_match_fully=True):
        round_matches = []

        for match_in_round in range(int(num_matches_in_round)):
            new_match = Match(False, tournament_round, match_in_round + 1)
            if num_matches_in_round > 1 or num_matches_in_round == 1 and self.double_elimination:
                if not new_match.loser_side:
                    winner_match_in_round = int(math.ceil(new_match.match_in_round / 2))
                    winner_reference = WINNER_SIDE + str(tournament_round + 1) + ':' + str(winner_match_in_round)
                    new_match.winner_match = winner_reference
                    if self.double_elimination:
                        loser_round = self.get_loser_round(tournament_round)
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

        for match_in_round in range(matches_in_round):
            new_match = Match(True, loser_bracket_round, match_in_round + 1)

            if loser_bracket_round < loser_configuration[str(self.bracket_size)]['number_of_rounds']:
                target_match_in_next_round = match_in_round
                if even:
                    target_match_in_next_round = math.ceil(match_in_round/2)
                target_match_in_next_round += 1
                new_match.winner_match = f'L{loser_bracket_round + 1}:{target_match_in_next_round}'
            round_matches.append(new_match)

        return round_matches

    def print_tournament_bracket(self):
        tourney_type = 'Double' if self.double_elimination else 'Single'
        print(f'{NUMBER_OF_PLAYERS_FOR_TOURNAMENT} Players in tournament / '
              f'{self.bracket_size} Players Bracket / {tourney_type} Elimination')
        print()

        print('Winner Side')
        for key in self.tournament_bracket[WINNER_SIDE]:
            print(f'Round {key}')
            for match in self.tournament_bracket[WINNER_SIDE][key]:
                print(match)
            print()

        print('Loser Side')
        for key in self.tournament_bracket[LOSER_SIDE]:
            print(f'Round {key}')
            for match in self.tournament_bracket[LOSER_SIDE][key]:
                print(match)
            print()


class Match:
    player1 = None
    player2 = None
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

    def __str__(self):
        match_reference = self.match_reference()
        string_val = f'<Match {match_reference} {self.player1} vs {self.player2}'
        if self.winner_match is not None:
            string_val += f' Winner={self.winner_match}'
        if self.loser_match is not None:
            string_val += f' Loser={self.loser_match}'
        string_val += '>'
        return string_val

    def match_reference(self):
        winner_or_loser = WINNER_SIDE if not self.loser_side else LOSER_SIDE
        return f'{winner_or_loser}{self.tournament_round}:{self.match_in_round}'


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    tournament = Tournament(NUMBER_OF_PLAYERS_FOR_TOURNAMENT, True)
    tournament.generate_bracket()
    tournament.print_tournament_bracket()
