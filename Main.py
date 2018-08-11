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
            cancel=False,
        ).run()

        if result:
            AlertWindow(
                "Notify",
                "Please choose the directory where java is installed as specific as you can.\n"
                "Program will search under the directory you provide.",
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
    app.load_board(load_from_image("test/sudoku1.jpg").board)
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

        # Draw board and pack canvas
        self.canvas = tk.Canvas(self, width=450, height=450)
        self.canvas.config(borderwidth=2)
        for hor in range(9):
            self.canvas.create_line(
                (0, hor * 50, 450, hor * 50), width=2 if hor % 3 == 0 else 1
            )
        for ver in range(9):
            self.canvas.create_line(
                (ver * 50, 0, ver * 50, 450), width=2 if ver % 3 == 0 else 1
            )
        self.canvas.bind("<Button-1>", self.click_board)
        self.canvas.pack(padx=10, pady=10)

        # Bind global events
        self.bind("<Key>", self.chess_control)
        self.bind("<Control-z>", self.withdraw)
        self.bind("<Control-s>")  # TODO
        self.bind("<BackSpace>", lambda e: self.clear_number(e, record=True))
        self.bind("<Delete>", lambda e: self.clear_number(e, record=True))
        self.bind("<Left>", self.move_select)
        self.bind("<Right>", self.move_select)
        self.bind("<Up>", self.move_select)
        self.bind("<Down>", self.move_select)

    def load_board(self, board: List[List[int]]):
        assert len(board) == len(board[0]) == 9
        self.board.setBoard(board)
        for x in range(9):
            for y in range(9):
                if self.board.board[x][y] != 0:
                    self.set_number((x, y), self.board.board[x][y], final=True, record=False)
                    self.original_state[x][y] = 1

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
                        block[0] * 50,
                        block[1] * 50,
                        (block[0] + 1) * 50,
                        (block[1] + 1) * 50,
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

    def set_number(self, block: Tuple[int, int], number: int, final: bool = False, record: bool = True) -> None:
        """
        Set the certain number on the board
        :param final: if this is true, number show on the board will be BOLD
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
            (block[0] * 50 + 25, block[1] * 50 + 25),
            text=str(number),
            font=Font(size=20,
                      weight=tk.font.BOLD if final else tk.font.NORMAL),
        )
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
                    self.canvas.delete(self.canvas_num[self.selected[0]][self.selected[1]])
                    if record:
                        if not self.operation_list:
                            self.operation_list.append(("clear", self.selected, num))
                        else:
                            if ("clear", self.selected) != self.operation_list[-1]:
                                self.operation_list.append(("clear", self.selected, num))

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
        return x // 50, y // 50

    def run(self):
        # Set mouse focus on main window so that app can receive key press signals
        self.focus_set()
        self.mainloop()


class AlertWindow(ttk.Frame):
    """
    This class show an alert window
    """
    result: bool

    def __init__(self, title: str, msg: str, cancel: bool = True):
        super(AlertWindow, self).__init__()

        self.result = False
        self.master.title(title)
        ttk.Label(self.master, text=msg).pack(padx=10, pady=10)

        self.buttonFrame = ttk.Frame(self)
        ttk.Button(self.buttonFrame, text="OK", command=self.ok).grid(
            row=0, column=0, padx=10
        )
        if not cancel:
            ttk.Button(self.buttonFrame, text="Cancel", command=self.cancel).grid(
                row=0, column=1, padx=10
            )

        self.buttonFrame.pack()
        self.pack()

    def run(self) -> bool:
        """
        Run the window, return user choice
        :return: True for select "OK" and False for select "Cancel"
        """
        self.master.mainloop()
        return self.result

    def ok(self):
        self.result = True
        self.master.destroy()

    def cancel(self):
        self.master.destroy()


if __name__ == "__main__":
    main()
