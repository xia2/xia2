#!/usr/bin/env python
#
# Tic Tac Toe, taken from:
#
# http://code.activestate.com/recipes/576661-tic-tac-toe/
#
# and heavily modified to be an easter egg of the computer playing against
# itself.

from __future__ import absolute_import, division, print_function

from random import *
from string import *

EMPTY = " "
PL_1 = "X"
PL_2 = "O"

A = "A"
B = "B"
C = "C"

board = [[EMPTY, EMPTY, EMPTY], [EMPTY, EMPTY, EMPTY], [EMPTY, EMPTY, EMPTY]]

current_player = randint(1, 2)


def square(row, col):
    return (row, col)


def square_row(square):
    return square[0]


def square_col(square):
    return square[1]


def get_square(square):
    """ Returns the value of the given square. """
    row_i = square_row(square) - 1
    col_i = ord(square_col(square)) - ord(A)
    return board[row_i][col_i]


def set_square(square, mark):
    """ Sets the value of the given square. """
    row_i = square_row(square) - 1
    col_i = ord(square_col(square)) - ord(A)
    board[row_i][col_i] = mark


def get_row(row):
    """ Returns the given row as a list of three values. """
    return [get_square((row, A)), get_square((row, B)), get_square((row, C))]


def get_column(col):
    """ Returns the given column as a list of three values. """
    return [get_square((1, col)), get_square((2, col)), get_square((3, col))]


def get_diagonal(corner_square):
    """Returns the diagonal that includes the given corner square.
    Only (1, A), (1, C), (3, A) and (3, C) are corner squares."""
    if corner_square == (1, A) or corner_square == (3, C):
        return [get_square((1, A)), get_square((2, B)), get_square((3, C))]
    else:
        return [get_square((1, C)), get_square((2, B)), get_square((3, A))]


def get_mark(player):
    """ Returns the mark of the given player (1 or 2). """
    if player == 1:
        return PL_1
    else:
        return PL_2


def all_squares_filled():
    """ Returns True iff all squares have been filled. """
    for row in range(1, 4):
        if EMPTY in get_row(row):
            return False
    return True


def player_has_won(player):
    """ Returns True iff the given player (1 or 2) has won the game. """

    MARK = get_mark(player)
    win = [MARK, MARK, MARK]

    if get_row(1) == win or get_row(2) == win or get_row(3) == win:
        return True

    if get_column(A) == win or get_column(B) == win or get_column(C) == win:
        return True

    if get_diagonal((1, A)) == win or get_diagonal((1, C)) == win:
        return True

    return False


def draw_board_straight():
    """ Returns a straight string representation of the board. """

    A1, A2, A3 = get_square((1, A)), get_square((2, A)), get_square((3, A))
    B1, B2, B3 = get_square((1, B)), get_square((2, B)), get_square((3, B))
    C1, C2, C3 = get_square((1, C)), get_square((2, C)), get_square((3, C))

    lines = []
    lines.append("")
    lines.append("+---+---+---+")
    lines.append("| " + A1 + " | " + B1 + " | " + C1 + " |")
    lines.append("+---+---+---+")
    lines.append("| " + A2 + " | " + B2 + " | " + C2 + " |")
    lines.append("+---+---+---+")
    lines.append("| " + A3 + " | " + B3 + " | " + C3 + " |")
    lines.append("+---+---+---+")
    lines.append("")

    return join(lines, "\n")


def draw_board():
    """ Returns a string representation of the board in its current state. """
    return draw_board_straight()


def reset_board():
    for row in (1, 2, 3):
        for col in (A, B, C):
            set_square(square(row, col), EMPTY)


def ttt():

    global current_player

    reset_board()
    current_player = randint(1, 2)

    player1_name = "Foo"
    player2_name = "Bar"

    def get_name(player):
        if player == 1:
            return player1_name
        else:
            return player2_name

    result = []

    result.append("Bored now. Quick games of noughts and crosses...")

    while not all_squares_filled():

        choices = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"]

        choice = choices[randint(0, 8)]

        if choice[0] in ["1", "2", "3"]:
            row = int(choice[0])
            col = upper(choice[1])
        else:
            row = int(choice[1])
            col = upper(choice[0])

        choice = square(row, col)

        if get_square(choice) != EMPTY:
            continue

        set_square(choice, get_mark(current_player))

        if player_has_won(current_player):
            for record in draw_board().split("\n"):
                result.append(record)

            result.append(
                "%s (%s) wins!" % (get_name(current_player), get_mark(current_player))
            )
            break

        if all_squares_filled():
            for record in draw_board().split("\n"):
                result.append(record)

            result.append("Draw...")
            break

        current_player = 3 - current_player

    result.append("")
    result.append("... ah, that' better!")

    return result


if __name__ == "__main__":

    result = ttt()
    for r in result:
        print(r)
