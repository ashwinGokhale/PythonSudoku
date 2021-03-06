#!/usr/bin/env python

# Modified code from:
#   http://newcoder.io/gui/
#   https://github.com/JoeKarlsson/Python-Sudoku-Generator-Solver

import argparse
import random
from copy import deepcopy
from tkinter import Tk, Canvas, Frame, Button, BOTH, TOP, BOTTOM, Menu, filedialog
from tkinter.filedialog import asksaveasfile

import numpy as np

BOARDS = ['debug', 'easy', 'hard', 'error', 'etc...']  # Available sudoku boards
DIFFICULTIES = ['easy', 'medium', 'hard']
MARGIN = 30  # Pixels around the board
SIDE = 50  # Width of every board cell.
WIDTH = HEIGHT = MARGIN * 2 + SIDE * 9  # Width and height of the whole board


class SudokuError(Exception):
    def __init__(self, *args):
        Exception.__init__(self, *args)
        self.value = args[0]

    def __str__(self):
        return self.value.encode('string_escape')


def parse_arguments():
    """
    Parses arguments of the form:
        pydoku.py <board name>
    Where `board name` must be in the `BOARD` list

    Difficulty:
        Easy: 32+ clues (49 or fewer holes)
        Medium: 27-31 clues (50-54 holes)
        Hard: 26 or fewer clues (54+ holes)
    """
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-b", "--board",
                            help="Desired board name",
                            type=str,
                            choices=BOARDS,
                            required=False)
    arg_parser.add_argument("-d", "--difficulty",
                            help="Desired difficulty",
                            type=str,
                            choices=DIFFICULTIES,
                            required=False)

    # Creates a dictionary of keys = argument flag, and value = argument
    args = vars(arg_parser.parse_args())
    return (args['board'], args['difficulty'])


class SudokuUI(Frame):
    """
    The Tkinter UI, responsible for drawing the board and accepting user input.
    """

    def __init__(self, parent, game):
        self.game = game
        self.game.start()
        Frame.__init__(self, parent)
        self.parent = parent
        self.row, self.col = -1, -1
        self.__initUI()

    def new_board(self, board=None, difficulty='easy'):
        self.game = SudokuGame(board, difficulty)
        self.game.start()
        self.row, self.col = -1, -1
        Frame.destroy(self)
        Frame.__init__(self, self.parent)
        self.__initUI()

    def open_board(self):
        f = filedialog.askopenfilename()
        if f is not None:
            self.new_board(open(f, 'r'))
            if self.game.board.checkWin():
                self.__draw_victory()

    def save_board(self):
        f = asksaveasfile(mode='w', defaultextension=".board")
        if f is not None:
            board = self.game.board.serialize()
            f.write(board)
            f.close()

    def give_up(self):
        self.game.board.board = self.game.board.solved_board
        self.__draw_puzzle()
        self.__draw_loss()


    def __initUI(self):
        self.parent.title("Pydoku")
        self.pack(fill=BOTH)
        give_up_button = Button(self, text="I give up", command=self.give_up)
        give_up_button.pack(fill=BOTH, side=TOP)
        self.canvas = Canvas(self, width=WIDTH, height=HEIGHT)
        self.canvas.pack(fill=BOTH, side=TOP)
        clear_button = Button(self, text="Clear answers", command=self.__clear_answers)
        clear_button.pack(fill=BOTH, side=BOTTOM)

        self.__draw_grid()
        self.__draw_puzzle()

        self.canvas.bind("<Button-1>", self.__cell_clicked)
        self.canvas.bind("<Key>", self.__key_pressed)

        """ 
        Add menu items to the parent 
        """
        menu = Menu(root)
        file_menu = Menu(menu)
        difficulty_options = Menu(file_menu)
        difficulty_options.add_command(label='Easy', command=lambda: self.new_board(None, 'easy'))
        difficulty_options.add_command(label='Medium', command=lambda: self.new_board(None, 'medium'))
        difficulty_options.add_command(label='Hard', command=lambda: self.new_board(None, 'hard'))
        file_menu.add_cascade(label="New", menu=difficulty_options)
        file_menu.add_command(label="Open", command=self.open_board)
        file_menu.add_command(label="Save", command=self.save_board)
        menu.add_cascade(label="File", menu=file_menu)
        self.parent.config(menu=menu)

    def __draw_grid(self):
        """
        Draws grid divided with blue lines into 3x3 squares
        """
        for i in range(10):
            color = "blue" if i % 3 == 0 else "gray"

            x0 = MARGIN + i * SIDE
            y0 = MARGIN
            x1 = MARGIN + i * SIDE
            y1 = HEIGHT - MARGIN
            self.canvas.create_line(x0, y0, x1, y1, fill=color)

            x0 = MARGIN
            y0 = MARGIN + i * SIDE
            x1 = WIDTH - MARGIN
            y1 = MARGIN + i * SIDE
            self.canvas.create_line(x0, y0, x1, y1, fill=color)

    def __draw_puzzle(self):
        self.canvas.delete("numbers")
        for i in range(9):
            for j in range(9):
                answer = self.game.board.board[i][j]
                if answer != 0:
                    x = MARGIN + j * SIDE + SIDE / 2
                    y = MARGIN + i * SIDE + SIDE / 2
                    original = self.game.start_puzzle[i][j]
                    color = "black" if answer == original else "sea green"
                    self.canvas.create_text(
                        x, y, text=answer, tags="numbers", fill=color
                    )

    def __draw_cursor(self):
        self.canvas.delete("cursor")
        if self.row >= 0 and self.col >= 0:
            x0 = MARGIN + self.col * SIDE + 1
            y0 = MARGIN + self.row * SIDE + 1
            x1 = MARGIN + (self.col + 1) * SIDE - 1
            y1 = MARGIN + (self.row + 1) * SIDE - 1
            self.canvas.create_rectangle(
                x0, y0, x1, y1,
                outline="red", tags="cursor"
            )

    def __draw_victory(self):
        # create a oval (which will be a circle)
        x0 = y0 = MARGIN + SIDE * 2
        x1 = y1 = MARGIN + SIDE * 7
        self.canvas.create_oval(
            x0, y0, x1, y1,
            tags="victory", fill="green", outline="orange"
        )
        # create text
        x = y = MARGIN + 4 * SIDE + SIDE / 2
        self.canvas.create_text(
            x, y,
            text="You win!", tags="victory",
            fill="white", font=("Arial", 32)
        )

    def __draw_loss(self):
        # create a oval (which will be a circle)
        x0 = y0 = MARGIN + SIDE * 2
        x1 = y1 = MARGIN + SIDE * 7
        self.canvas.create_oval(
            x0, y0, x1, y1,
            tags="loss", fill="red", outline="red"
        )
        # create text
        x = y = MARGIN + 4 * SIDE + SIDE / 2
        self.canvas.create_text(
            x, y,
            text="You Lose!\n      =(", tags="loss",
            fill="white", font=("Arial", 32)
        )

    def __cell_clicked(self, event):
        if self.game.game_over:
            return
        x, y = event.x, event.y
        if (MARGIN < x < WIDTH - MARGIN and MARGIN < y < HEIGHT - MARGIN):
            self.canvas.focus_set()

            # get row and col numbers from x,y coordinates
            row, col = int((y - MARGIN) / SIDE), int((x - MARGIN) / SIDE)

            # Set the row and column
            self.row, self.col = row, col
        else:
            self.row, self.col = -1, -1

        self.__draw_cursor()

    def __key_pressed(self, event):
        # Do nothing if game over or trying to change black number
        if self.game.game_over or self.game.board.board[self.row][self.col] == self.game.start_puzzle[self.row][
            self.col]:
            return

        # Otherwise, if char is a number, assign it in the board and redraw
        if self.row >= 0 and self.col >= 0 and event.char in "1234567890":
            self.game.board.board[self.row][self.col] = self.game.board.board[self.row][self.col]
            self.game.board.board[self.row][self.col].setAnswer(int(event.char))
            self.col, self.row = -1, -1
            self.__draw_puzzle()
            self.__draw_cursor()
            if self.game.board.checkWin():
                self.__draw_victory()

    def __clear_answers(self):
        self.game.start()
        self.canvas.delete("victory")
        self.canvas.delete("loss")
        self.__draw_puzzle()


class SudokuBoard(object):
    """
    Sudoku Board representation
    """

    def __init__(self, board_file, difficulty="easy"):
        if not board_file:
            self.board = self.generateBoard()
            while not self.checkWin():
                self.board = self.generateBoard()
            self.solved_board = deepcopy(self.board)
            self.makeHoles(difficulty)
        else:
            self.board = self.__create_from_file(board_file)

    def checkWin(self):
        for row in range(9):
            if not self.__check_row(row):
                return False
        for column in range(9):
            if not self.__check_column(column):
                return False
        for row in range(3):
            for column in range(3):
                if not self.__check_square(row, column):
                    return False
        self.game_over = True
        return True

    def __check_block(self, block):
        return set(block) == set(range(1, 10))

    def __check_row(self, row):
        return self.__check_block([i.answer for i in self.board[row]])

    def __check_column(self, column):
        return self.__check_block(
            [self.board[row][column].answer for row in range(9)]
        )

    def __check_square(self, row, column):
        return self.__check_block(
            [
                self.board[r][c].answer
                for r in range(row * 3, (row + 1) * 3)
                for c in range(column * 3, (column + 1) * 3)
                ]
        )

    def emptyBoard(self):
        board = np.zeros((9, 9), dtype=Cell)

        for row in range(9):
            for col in range(9):
                box = 0
                if row in [0, 1, 2]:
                    box += 1
                if row in [3, 4, 5]:
                    box += 4
                if row in [6, 7, 8]:
                    box += 7

                if col in [0, 1, 2]:
                    box += 0
                if col in [3, 4, 5]:
                    box += 1
                if col in [6, 7, 8]:
                    box += 2

                board[row][col] = (Cell(row, col, box))

        return board

    def __create_from_file(self, board_file):
        board = np.zeros((9, 9), dtype=Cell)

        row = 0
        for line in board_file:
            line = line.strip()
            if len(line) != 9:
                raise SudokuError("Each line in the sudoku puzzle must be 9 chars long.")
            col = 0
            for c in line:
                if not c.isdigit():
                    raise SudokuError("Valid characters for a sudoku puzzle must be in 0-9")

                box = 0
                if row in [0, 1, 2]:
                    box += 1
                if row in [3, 4, 5]:
                    box += 4
                if row in [6, 7, 8]:
                    box += 7

                if col in [0, 1, 2]:
                    box += 0
                if col in [3, 4, 5]:
                    box += 1
                if col in [6, 7, 8]:
                    box += 2

                board[row][col] = (Cell(row, col, box))
                board[row][col].setAnswer(int(c))
                col += 1

            row += 1

        if len(board) != 9:
            raise SudokuError("Each sudoku puzzle must be 9 lines long")

        return board

    def generateBoard(self):
        sudoku = self.emptyBoard().flatten().tolist()
        cells = [i for i in range(81)]

        while len(cells) > 0:
            m = min([sudoku[i].lenOfPossible() for i in cells])
            Lowest = [x for x in (sudoku[i] for i in cells if (sudoku[i].lenOfPossible() == m))]
            element = random.choice(Lowest)
            index = sudoku.index(element)
            cells.remove(index)

            if not element.solved:
                element.setAnswer(random.choice(element.possibleAnswers))
                for i in cells:
                    if element.row == sudoku[i].row:
                        sudoku[i].remove(element.answer)
                    if element.col == sudoku[i].col:
                        sudoku[i].remove(element.answer)
                    if element.box == sudoku[i].box:
                        sudoku[i].remove(element.answer)

            else:
                element.setAnswer(element.returnSolved())
                for i in cells:
                    if element.row == sudoku[i].row:
                        sudoku[i].remove(element.answer)
                    if element.col == sudoku[i].col:
                        sudoku[i].remove(element.answer)
                    if element.box == sudoku[i].box:
                        sudoku[i].remove(element.answer)

        return np.array(sudoku).reshape((9, 9))

    def makeHoles(self, difficulty):
        """
        :param difficulty: Easy: 32+ clues (49 or fewer holes)
                           Medium: 27-31 clues (50-54 holes)
                           Hard: 26 or fewer clues (54+ holes)
        """

        toMake = 49 if difficulty == 'easy' else 54 if difficulty == 'medium' else 60
        squaresLeft = 81
        holesLeft = float(toMake)

        for i in range(9):
            for j in range(9):
                chance = holesLeft / squaresLeft
                if (random.random() <= chance):
                    self.board[i][j].hole()
                    holesLeft -= 1

                squaresLeft -= 1

    def serialize_matrix(self, board):
        '''Converts board to a 9x9 numpy matrix'''
        rows = [[0 for i in range(9)] for j in range(9)]
        for i in range(9):
            for j in range(9):
                rows[i][j] = (board[i][j].answer)
        return rows

    def serialize(self):
        '''Converts 9x9 numpy matrix board to a string that can be written to a file'''
        return '\n'.join([''.join(map(str, i)) for i in self.serialize_matrix(self.board)])

    def printBoard(self, board):
        '''Prints out a sudoku in a format that is easy for a human to read'''
        print(np.matrix(self.serialize_matrix(board)))




class SudokuGame(object):
    """
    A Sudoku game, in charge of storing the state of the board and checking
    whether the puzzle is completed.
    """

    def __init__(self, board_file, difficulty="easy"):
        self.board_file = board_file
        self.board = SudokuBoard(board_file, difficulty)
        self.start_puzzle = deepcopy(self.board.board)

    def start(self):
        self.game_over = False
        for i in range(9):
            for j in range(9):
                if self.start_puzzle[i][j].answer != 0:
                    self.board.board[i][j] = self.start_puzzle[i][j]
                else:
                    self.board.board[i][j] = deepcopy(self.start_puzzle[i][j])


class Cell(object):
    def __init__(self, x, y, z):
        self.row = x
        self.col = y
        self.box = z
        self.solved = False
        self.possibleAnswers = [i for i in range(1, 10)]
        self.answer = 0

    def remove(self, num):
        if num in self.possibleAnswers and self.solved == False:
            self.possibleAnswers.remove(num)
            if len(self.possibleAnswers) == 1:
                self.answer = self.possibleAnswers[0]
                self.solved = True
        if num in self.possibleAnswers and self.solved == True:
            self.answer = 0

    def setAnswer(self, num):
        self.solved = True
        self.answer = num
        self.possibleAnswers = [num]

    def lenOfPossible(self):
        return len(self.possibleAnswers)

    def returnSolved(self):
        return self.possibleAnswers[0] if self.solved else 0

    def hole(self):
        """ Resets all attributes of a cell to the original conditions"""
        self.possibleAnswers = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        self.answer = 0
        self.solved = False

    def __str__(self):
        return '{}'.format(self.answer)

if __name__ == '__main__':
    args = parse_arguments()
    board_name = args[0] if args[0] else None
    difficulty = args[1] if args[1] else 'easy'
    game = SudokuGame(board_name, difficulty)
    root = Tk()
    SudokuUI(root, game)
    root.geometry("%dx%d" % (WIDTH, HEIGHT + 70))
    root.mainloop()
