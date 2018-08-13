import json
import os
import pickle
import tkinter as tk
import tkinter.ttk as ttk
from collections import namedtuple
from tkinter.font import Font
from typing import Tuple, List

import easygui
import jpype
from jpype._jvmfinder import JVMNotFoundException

from operateImage import *


def start_jvm(path: str = None):
    if path:
        print("Java path: " + path)
        jpype.startJVM(path, r"-Djava.class.path=sudoku.jar")
        return path

    try:
        j_path: Union[bytes, str] = jpype.getDefaultJVMPath()
    except JVMNotFoundException:
        j_path = ""

        result: bool = AlertWindow(
            "Error",
            "JVM cannot be located.\n"
            "Please ensure you have installed java(>= 1.8) on your computer.\n"
            "If you have installed java, please choose location of java manually.",
            True
        ).run()

        if result:
            AlertWindow(
                "Notify",
                "Please choose the directory where java is installed as specific as you can.\n"
                "Program will search under the directory you provide.",
                False
            ).run()
            root = easygui.diropenbox(
                "Choose the directory where java is installed", "Locate JVM"
            )
            if not root:
                exit(-1)
            for dirs, _, file in os.walk(root):
                if "jvm.dll" in file:
                    j_path = dirs + r"\jvm.dll"
                    print("Java path: " + j_path)
                    break
            else:
                AlertWindow(
                    "Error",
                    "No JVM found, please make sure you choose the right directory.",
                    False
                )
                exit(-1)
    jpype.startJVM(j_path, r"-Djava.class.path=sudoku.jar")
    return j_path


def main():
    user_config = {}
    if "userConfig.json" in os.listdir(os.getcwd()):
        with open("userConfig.json") as f:
            user_config: dict = json.load(f)

    # Look for JVM...
    if ("jvmPath" in user_config.keys()) and (user_config["jvmPath"]):
        start_jvm(user_config["jvmPath"])
    else:
        user_config["jvmPath"] = start_jvm()
    with open("userConfig.json", "w") as f:
        json.dump(user_config, f)

    # Start APP...
    app = App()
    # app.load_board(load_from_image("test/sudoku1.jpg").board)
    app.run()


def load_from_image(img_name: str):
    board = []
    with open("train.module", "rb") as f:
        train_data = pickle.load(f)
    img = optimize_board(Image.open(img_name))
    line = 0
    temp = []
    fail = []
    count = 1
    for grid in split_board(img):
        count += 1
        try:
            feature = get_image_feature(grid)
        except AssertionError:
            print("fail at ", count)
            temp.append(0)
            fail.append((count % 9, count // 9))
            continue
        if feature:
            temp.append(ocr(train_data, np.array(feature)))
        else:
            temp.append(0)
        if line == 8:
            line = 0
            board.append(temp[:])
            temp = []
        else:
            line += 1
    out = namedtuple("GeneratedBoard", ["board", "fail"])
    out.board = board
    out.fail = fail
    return out


class App(tk.Tk):
    def __init__(self):
        super(App, self).__init__()
        self.title("Sudoku")
        self.resizable(False, False)

        # Java chessboard object
        self.board = jpype.JClass("javaGame.Board")()

        # Store the puzzle generated, don't let user change it during the game
        self.original_state = [[0 for x in range(9)] for y in range(9)]

        # Store all text number created on canvas
        self.canvas_num = [[None for x in range(9)] for y in range(9)]

        # Store the four lines of the block user selected last time
        self.last_select: Tuple[tk.Canvas.create_rectangle, tuple] = None

        # The current block selected by user, none if not select yet or selected block cannot be changed
        self.selected = None

        # Record all operations, used for withdraw
        self.operation_list = []

        # Store all warning blocks
        self.warning_block_list = []

        # Draw board and pack canvas
        self.canvas = tk.Canvas(self, width=270, height=270)
        self.canvas.config(borderwidth=2)
        for hor in range(9):
            self.canvas.create_line(
                (0, hor * 30, 270, hor * 30), width=2 if hor % 3 == 0 else 1
            )
        for ver in range(9):
            self.canvas.create_line(
                (ver * 30, 0, ver * 30, 270), width=2 if ver % 3 == 0 else 1
            )
        self.canvas.bind("<Button-1>", self.click_board)
        self.canvas.grid(row=0, column=0, padx=10, pady=10)

        # Add toolbox
        self.toolbox = ttk.Frame(self)
        self.control_frame = ttk.Labelframe(self.toolbox, text="Control board")
        ttk.Button(self.control_frame, text="Check", command=self.check).pack(
            padx=10, pady=3
        )
        ttk.Button(self.control_frame, text="Reset", command=self.reset).pack(
            padx=10, pady=3
        )
        ttk.Button(self.control_frame, text="Solve", command=self.solve).pack(
            padx=10, pady=3
        )
        self.control_frame.pack(pady=3)
        self.load_frame = ttk.Labelframe(self.toolbox, text="Create & Load board")
        ttk.Button(
            self.load_frame,
            text="Random Generate",
            command=self.random_generate,
            width=15,
        ).pack(padx=10, pady=3)
        ttk.Button(
            self.load_frame,
            text="Load from disk",
            command=self.load_from_disk,
            width=15,
        ).pack(padx=10, pady=3)
        ttk.Button(
            self.load_frame,
            text="Load from picture",
            command=self.load_from_picture,
            width=15,
        ).pack(padx=10, pady=3)
        self.load_frame.pack(pady=2)
        self.toolbox.grid(row=0, column=1)

        # Bind global events
        self.bind("<Key>", self.chess_control)
        self.bind("<Control-z>", self.withdraw)
        self.bind("<BackSpace>", lambda e: self.clear_number(e, record=True))
        self.bind("<Delete>", lambda e: self.clear_number(e, record=True))
        self.bind("<Left>", self.move_select)
        self.bind("<Right>", self.move_select)
        self.bind("<Up>", self.move_select)
        self.bind("<Down>", self.move_select)

    def solve(self):
        self.board.setBoard(self.original_state)
        if not self.board.solvePuzzle():
            AlertWindow("Error", "Cannot solve this board!", False).run()
            return
        for i in range(9):
            for j in range(9):
                if not self.original_state[i][j]:
                    self.set_number((i, j), self.board.board[i][j], record=False)

    def reset(self):
        self.board.setBoard([[0 for x in range(9)] for y in range(9)])
        self.show_board()

    def check(self):
        for _ in range(len(self.warning_block_list)):
            self.canvas.delete(self.warning_block_list.pop()[0])

        error_list = []
        for i in range(9):
            for j in range(9):
                if not self.original_state[i][j]:
                    if not self.board.checkValidity(i, j):
                        error_list.append((i, j))
        for block in error_list:
            self.warning_block_list.append(
                (
                    self.canvas.create_rectangle(
                        (
                            block[0] * 30,
                            block[1] * 30,
                            (block[0] + 1) * 30,
                            (block[1] + 1) * 30,
                        ),
                        outline="Purple",
                        width=2,
                    ),
                    block,
                )
            )
        if not error_list:
            AlertWindow("Congratulation", "No problems found so far!", False).run()

    def random_generate(self):
        self.board.setBoard([[0 for x in range(9)] for y in range(9)])
        self.board.randomGenerateBoard()
        self.board.generatePuzzle(30, 60)
        self.show_board()

    def load_from_disk(self):
        pass

    def load_from_picture(self):
        pass

    def load_board(self, board: List[List[int]]):
        """
        Load board from existing data
        :param board: 9 * 9 2d array represent the board
        :return: None
        """
        assert len(board) == len(board[0]) == 9
        self.board.setBoard(board)
        self.show_board()

    def show_board(self):
        # reset board
        self.original_state = [[0 for x in range(9)] for y in range(9)]
        self.operation_list = []
        for i in self.canvas_num:
            for j in i:
                self.canvas.delete(j)
        self.canvas_num = [[None for x in range(9)] for y in range(9)]

        for x in range(9):
            for y in range(9):
                if self.board.board[x][y] != 0:
                    self.set_number(
                        (x, y),
                        self.board.board[x][y],
                        font=tk.font.BOLD,
                        color="black",
                        record=False,
                    )
                    self.original_state[x][y] = self.board.board[x][y]

    def withdraw(self, e: tk.Event = None) -> None:
        """
        When user press ctrl + z or select withdraw button, this function will be called
        :param e: tk Event, can be empty
        :return: None
        """
        print("withdraw: ", self.operation_list)
        if not self.operation_list:
            return
        last_operate = self.operation_list.pop()
        if last_operate[0] == "set":
            self.clear_number(position=last_operate[1])
            # If user just change number instead of setting it for the first time
            if not self.operation_list:
                return
            if last_operate[:2] == self.operation_list[-1][:2]:
                self.set_number(
                    self.operation_list[-1][1], self.operation_list[-1][2], False
                )
        elif last_operate[0] == "clear":
            self.set_number(block=last_operate[1], number=last_operate[2], record=False)

    def click_board(self, e) -> None:
        """
        When user click canvas, this function will be called.
        This function control the block selected by user
        :param e: tk event (mouse click)
        :return: None
        """
        # print(e.x, e.y)
        self.select_block(self._get_block(e.x, e.y))
        # print("select:", self.selected)

    def select_block(self, block: tuple) -> None:
        """
        Show the block selected by user
        :param block: coordinate of block
        :return: None
        """
        last_coo = None
        if self.last_select:
            # print(self.last_select)
            self.canvas.delete(self.last_select[0])
            last_coo = self.last_select[1]

        if not last_coo or last_coo != block:
            self.last_select = (
                self.canvas.create_rectangle(
                    (
                        block[0] * 30,
                        block[1] * 30,
                        (block[0] + 1) * 30,
                        (block[1] + 1) * 30,
                    ),
                    outline="blue"
                    if self.original_state[block[0]][block[1]] == 0
                    else "red",
                    width=3,
                ),
                block,
            )
        elif last_coo == block:
            self.last_select = None

        self.selected = (
            block
            # if self.original_state[block[0]][block[1]] == 0 and self.last_select
            # else None
        )

    def chess_control(self, event: tk.Event = None):
        """
        When user press keyboard in canvas, this function will be called.
        :param event: tk event, can be empty
        :return: None
        """
        num = event.char
        if num and num in "123456789":
            if self.selected:
                if self.original_state[self.selected[0]][self.selected[1]] == 0:
                    self.set_number(self.selected, int(num))

    def set_number(
            self,
            block: Tuple[int, int],
            number: int,
            font=tk.font.NORMAL,
            color: str = "green",
            record: bool = True,
    ) -> None:
        """
        Set the certain number on the board
        :param color: the color of the number
        :param font: the font of number
        :param block: coordinate of the block
        :param number: number want to show
        :param record: will this operation be record in self.operation_list
        :return: None
        """
        assert 1 <= number <= 9
        self.board.board[block[0]][block[1]] = number
        if self.canvas_num[block[0]][block[1]]:
            self.canvas.delete(self.canvas_num[block[0]][block[1]])

        self.canvas_num[block[0]][block[1]] = self.canvas.create_text(
            (block[0] * 30 + 15, block[1] * 30 + 15),
            text=str(number),
            font=Font(size=15, weight=font),
            fill=color,
        )

        # Check if this is a warned block
        for i in self.warning_block_list:
            if i[1] == block:
                self.canvas.delete(i[0])
                self.warning_block_list.remove(i)
                break

        if record:
            if not self.operation_list:
                self.operation_list.append(("set", self.selected, number))
            else:
                if ("set", self.selected, number) != self.operation_list[-1]:
                    self.operation_list.append(("set", self.selected, number))

    def clear_number(
            self, e=None, position: Tuple[int, int] = None, record: bool = False
    ) -> None:
        """
        This function will be called when user press "Delete" or "BackSpace" key
        :param e: tk event, can be empty
        :param position:  coordinate of block (if e is empty, this parameter should be filled)
        :param record: will this operation be record in self.operation_list
        :return: None
        """
        if e:
            print(e.keysym)
        if position:
            num = self.board.board[position[0]][position[1]]
            self.board.board[position[0]][position[1]] = 0
            if self.canvas_num[position[0]][position[1]]:
                self.canvas.delete(self.canvas_num[position[0]][position[1]])
                if record:
                    if not self.operation_list:
                        self.operation_list.append(("clear", self.selected, num))
                    else:
                        if ("clear", self.selected) != self.operation_list[-1]:
                            self.operation_list.append(("clear", self.selected, num))
            return

        # tk event as input
        if self.selected:
            if self.original_state[self.selected[0]][self.selected[1]] == 0:
                num = self.board.board[self.selected[0]][self.selected[1]]
                self.board.board[self.selected[0]][self.selected[1]] = 0
                if self.canvas_num[self.selected[0]][self.selected[1]]:
                    self.canvas.delete(
                        self.canvas_num[self.selected[0]][self.selected[1]]
                    )
                    if record:
                        if not self.operation_list:
                            self.operation_list.append(("clear", self.selected, num))
                        else:
                            if ("clear", self.selected) != self.operation_list[-1]:
                                self.operation_list.append(
                                    ("clear", self.selected, num)
                                )

    def move_select(self, e) -> None:
        """
        WHen user press any of the four direction keys, this function will be called
        :param e: tk event (key press)
        :return: None
        """
        key = e.keysym
        if not self.selected:
            return
        if key == "Up":
            coo = list(self.selected)
            if coo[1] == 0:
                return
            coo[1] -= 1
            self.selected = tuple(coo)
            self.select_block(self.selected)
        elif key == "Down":
            coo = list(self.selected)
            if coo[1] == 8:
                return
            coo[1] += 1
            self.selected = tuple(coo)
            self.select_block(self.selected)
        elif key == "Left":
            coo = list(self.selected)
            if coo[0] == 0:
                if coo[1] == 0:
                    return
                # When get to the left end of a line,
                # continue press "left" will move to the above line
                coo[1] -= 1
                coo[0] = 8
            else:
                coo[0] -= 1
            self.selected = tuple(coo)
            self.select_block(self.selected)
        elif key == "Right":
            coo = list(self.selected)
            if coo[0] == 8:
                if coo[1] == 8:
                    return
                # When get to the right end of a line,
                # continue press "right" will move to the next line
                coo[0] = 0
                coo[1] += 1
            else:
                coo[0] += 1
            self.selected = tuple(coo)
            self.select_block(self.selected)

    @staticmethod
    def _get_block(x: int, y: int):
        return x // 30, y // 30

    def run(self):
        # Set mouse focus on main window so that app can receive key press signals
        self.focus_set()
        self.mainloop()


class AlertWindow(tk.Toplevel):
    """
    This class show an alert window
    """

    result: bool

    def __init__(self, title: str, msg: str, cancel_button: bool = True):
        super(AlertWindow, self).__init__()

        self.result = False
        self.title(title)
        ttk.Label(self, text=msg).grid(row=0, column=0, padx=10, pady=10)

        self.buttonFrame = ttk.Frame(self)
        ttk.Button(self.buttonFrame, text="OK", command=self.ok).grid(
            row=0, column=0, padx=10
        )
        if cancel_button:
            ttk.Button(self.buttonFrame, text="Cancel", command=self.cancel).grid(
                row=0, column=1, padx=10
            )

        self.buttonFrame.grid(row=1, column=0)

    def run(self) -> bool:
        """
        Run the window, return user choice
        :return: True for select "OK" and False for select "Cancel"
        """
        self.mainloop()
        return self.result

    def ok(self):
        self.result = True
        self.destroy()

    def cancel(self):
        self.destroy()


if __name__ == "__main__":
    main()
