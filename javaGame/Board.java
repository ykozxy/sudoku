package javaGame;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Random;

public class Board {
  private static final HashSet<Integer> cases = new HashSet<>();
  private final Random random = new Random();
  private int[][] board;

  public Board() {
    this(new int[9][9]);
  }

  public Board(int[][] data) {
    for (int i = 1; i < 10; i++) {
      cases.add(i);
    }
    board = data;
  }

  public static void main(String[] args) {
    System.out.println(Arrays.deepToString(new Board().board));
  }

  public void setBoard(int[][] board) {
    if (board.length != 9 || board[0].length != 9) {
      throw new ArrayIndexOutOfBoundsException();
    }
    this.board = board;
  }

  @Override
  public String toString() {
    StringBuilder out = new StringBuilder(), temp;
    out.append("-----------------------------\n");
    int count = 0;
    for (int[] row :
            this.board) {
      temp = new StringBuilder();
      for (int each :
              row) {
        temp.append((each == 0) ? "   " : (each + "  "));
      }
      temp.insert(8, "  ");
      temp.insert(19, "  ");
      if (count == 3 || count == 6) {
        out.append("                             \n");
      }
      out.append(temp).append("\n");
      count++;
    }
    out.append("-----------------------------\n");
    return String.valueOf(out);
  }

  private void setNumber(int row, int column, int val) throws IndexOutOfBoundsException, ValueOutOfRangeException {
    if (row > 8 || column > 8) throw new IndexOutOfBoundsException(String.valueOf(row) + column);
    if (val < 0 || val > 9) throw new ValueOutOfRangeException();
    this.board[row][column] = val;
  }

  public void randomGenerateBoard() {
    long startTime = System.currentTimeMillis();
    this.generatorCalculate(0, 0);
    System.out.printf("Board generated at %.3fs\n", (System.currentTimeMillis() - startTime) / 1000.0);
  }

  private boolean generatorCalculate(int row, int column) {
    HashSet<Integer> result = findFitNum(row, column);
    if (result.isEmpty()) {
      return false;
    }

    int[] candidateQueue = shuffle(result);
    int newRow, newColumn;
    for (int e : candidateQueue) {
      this.setNumber(row, column, e);
      newRow = row;
      newColumn = column + 1;
      if (newColumn > 8) {
        newColumn = 0;
        newRow++;
      }
      if (newRow > 8) {
        return true;
      }

      if (this.generatorCalculate(newRow, newColumn)) {
        return true;
      }
      this.setNumber(row, column, 0);
    }
    return false;
  }

  public int generatePuzzle(int lowerLimit, int upperLimit) {
    int numSpace = random.nextInt(upperLimit - lowerLimit) + lowerLimit;
    HashSet<int[]> visited = new HashSet<>();
    int row, column;
    int[] coordinate;
    for (int i = 0; i < numSpace; i++) {
      row = random.nextInt(9);
      column = random.nextInt(9);
      coordinate = new int[]{row, column};
      if (visited.contains(coordinate)) {
        continue;
      }

      visited.add(coordinate);
      this.setNumber(row, column, 0);
    }
    return numSpace;
  }

  public boolean solvePuzzle() {
    long startTime = System.currentTimeMillis();
    boolean result;
    int retryTIme = 5;
    do {
      result = this.solverCalculate(0, 0);
    } while (!result && retryTIme-- >= 0);
    if (retryTIme <= 0) {
      System.out.println("Solve puzzle failed!");
      return false;
    }
    System.out.printf("Solved puzzle at %.3fs\n", (System.currentTimeMillis() - startTime) / 1000.0);
    return true;
  }

  private boolean solverCalculate(int row, int column) {
    int newRow, newColumn;
    if (this.board[row][column] != 0) {
      newRow = row;
      newColumn = column + 1;
      if (newColumn > 8) {
        newColumn = 0;
        newRow++;
      }
      if (newRow > 8) {
        return true;
      }

      return this.solverCalculate(newRow, newColumn);
    }

    HashSet<Integer> result = findFitNum(row, column);
    if (result.isEmpty()) {
      return false;
    }

    int[] candidateQueue = shuffle(result);

    for (int e : candidateQueue) {
      this.setNumber(row, column, e);
      newRow = row;
      newColumn = column + 1;
      if (newColumn > 8) {
        newColumn = 0;
        newRow++;
      }
      if (newRow > 8) {
        return true;
      }

      if (this.solverCalculate(newRow, newColumn)) {
        return true;
      }
      this.setNumber(row, column, 0);
    }
    return false;
  }

  private int[] shuffle(HashSet<Integer> set) {
    int[] list = new int[set.size()];
    int p = 0;
    for (Integer t : set) {
      list[p] = t;
      p++;
    }

    int changeWith, temp;
    for (int i = 0; i < list.length; i++) {
      changeWith = random.nextInt(list.length);
      temp = list[changeWith];
      list[changeWith] = list[i];
      list[i] = temp;
    }
    return list;
  }

  public boolean checkValidity(int row, int column) {
    return !findFitNum(row, column).isEmpty();
  }

  public boolean checkValidityBoard() {
    for (int i = 0; i < 9; i++) {
      for (int j = 0; j < 9; j++) {
        if (!findFitNum(i, j).isEmpty()) {
          return false;
        }
      }
    }
    return true;
  }

  private HashSet<Integer> findFitNum(int row, int column) {
    HashSet<Integer> currentCases = new HashSet<>(cases);

    for (int i :
            this.board[row]) {
      currentCases.remove(i);
    }

    for (int i = 0; i < 9; i++) {
      currentCases.remove(this.board[i][column]);
    }

    for (int i :
            get_block(row, column)) {
      currentCases.remove(i);
    }

    return currentCases;
  }


  private int[] get_block(int row, int column) {
    int block;
    if (row < 3) {
      if (column < 3) {
        block = 1;
      } else if (column < 6) {
        block = 2;
      } else {
        block = 3;
      }
    } else if (row < 6) {
      if (column < 3) {
        block = 4;
      } else if (column < 6) {
        block = 5;
      } else {
        block = 6;
      }
    } else {
      if (column < 3) {
        block = 7;
      } else if (column < 6) {
        block = 8;
      } else {
        block = 9;
      }
    }

    int rowStartIndex = 0, columnStartIndex = 0;
    switch (block) {
      case 1:
        break;
      case 2:
        columnStartIndex = 3;
        break;
      case 3:
        columnStartIndex = 6;
        break;
      case 4:
        rowStartIndex = 3;
        break;
      case 5:
        rowStartIndex = 3;
        columnStartIndex = 3;
        break;
      case 6:
        rowStartIndex = 3;
        columnStartIndex = 6;
        break;
      case 7:
        rowStartIndex = 6;
        break;
      case 8:
        rowStartIndex = 6;
        columnStartIndex = 3;
        break;
      case 9:
        rowStartIndex = 6;
        columnStartIndex = 6;
        break;
      default:
        throw new ValueOutOfRangeException(String.valueOf(block));
    }

    int[] out = new int[9];
    int count = 0;
    for (int i = rowStartIndex; i < rowStartIndex + 3; i++) {
      for (int j = columnStartIndex; j < columnStartIndex + 3; j++) {
        out[count] = this.board[i][j];
        count++;
      }
    }

    return out;
  }

  public String getJdkVersion() {
    return System.getProperty("java.version");
  }
}


class ValueOutOfRangeException extends RuntimeException {
  ValueOutOfRangeException() {
    super();
  }

  ValueOutOfRangeException(String s) {
    super(s);
  }
}
