#!/usr/bin/env python

import sys
import copy
import collections
import time
import heapq
import random

bar = 4
width = 10
depth = 20

moves = ['L', 'R', 'D', 'U']

# workaround instead of OrderedDict
pieces_inorder = ['S', 'Z', 'O', 'I', 'L', 'J', 'T']
pieces_info = {
    'S': [
        { 'x': 1, 'y': 2 },
        { 'x': 2, 'y': 1 },
        { 'x': 2, 'y': 2 },
        { 'x': 3, 'y': 1 }
    ],
    'Z': [
        { 'x': 1, 'y': 1 },
        { 'x': 2, 'y': 1 },
        { 'x': 2, 'y': 2 },
        { 'x': 3, 'y': 2 }
    ],
    'O': [
        { 'x': 1, 'y': 1 },
        { 'x': 1, 'y': 2 },
        { 'x': 2, 'y': 1 },
        { 'x': 2, 'y': 2 }
    ],
    'I': [
        { 'x': 0, 'y': 1 },
        { 'x': 1, 'y': 1 },
        { 'x': 2, 'y': 1 },
        { 'x': 3, 'y': 1 }
    ],
    'L': [
        { 'x': 1, 'y': 1 },
        { 'x': 1, 'y': 2 },
        { 'x': 2, 'y': 1 },
        { 'x': 3, 'y': 1 }
    ],
    'J': [
        { 'x': 1, 'y': 1 },
        { 'x': 1, 'y': 2 },
        { 'x': 1, 'y': 3 },
        { 'x': 2, 'y': 1 }
    ],
    'T': [
        { 'x': 1, 'y': 1 },
        { 'x': 2, 'y': 1 },
        { 'x': 2, 'y': 2 },
        { 'x': 3, 'y': 1 }
    ]
}

class PieceState:
    class Cell:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    def __init__(self, piece):
        self.piece = piece
        self.x = (width - 4) / 2
        self.y = 0
        self.o = 0

    def cells(self):
        for cell in pieces_info[self.piece + str(self.o)]:
            yield self.Cell(self.x + cell['x'], self.y + cell['y'])

class Well:
    def __init__(self, init_board_str = ''):
        self.board = [0] * depth
        self.replay = []
        
        x = 0
        y = 0
        for c in init_board_str:
            if c in ':.#*':
                if c == '*':
                    self.set(x, y)
                
                x = x + 1
                if x == width:
                    y = y + 1
                    x = 0

    def __lt__(self, other):
        return self.board.__lt__(other.board) 

    def __eq__(self, other):
        return self.board.__eq__(other.board) 

    def __hash__(self):
        ret = 0
        for i in range(depth):
            ret = (ret << width) + ret
        return ret

    # returns True if the cell (x, y) in well is occupied
    def get(self, x, y):
        assert x >= 0 and x < width
        assert y >= 0 and y < depth
        return (self.board[y] >> x) % 2 == 1

    def set(self, x, y):
        assert not self.get(x, y)
        self.board[y] = self.board[y] | (1 << x)

    def dump(self, piece_state = None):
        print
        for y in range(depth):
            for x in range(width):
                c = '.'
                if y < bar:
                    c = ':'
                if piece_state != None:
                    for cell in piece_state.cells():
                        if x == cell.x and y == cell.y:
                            c = '#'
                if self.get(x, y):
                    c = '*'

                print c,
            print
        print '-' * (width * 2 - 1)

    # returns # of removed lines (0 if none, -1 if gameover)
    def add(self, piece_state):
        for cell in piece_state.cells():
            self.set(cell.x, cell.y)

        # gameover check
        for y in range(bar):
            if self.board[y]:
                return -1

        # calculate score
        removed_lines = 0
        y = depth - 1
        while y >= 1:
            if self.board[y] == (1 << width) - 1:
                removed_lines += 1
                for y2 in range(y, 0, -1):
                    self.board[y2] = self.board[y2 - 1]
            else:
                y -= 1

        return removed_lines

    def append_replay(self, s):
        self.replay.append(s)

    def get_replay(self):
        return ' '.join(self.replay)

    def collision(self, piece_state):
        for cell in piece_state.cells():
            if cell.x < 0 or cell.x >= width:
                return True
            if cell.y < 0 or cell.y >= depth:
                return True
            if self.get(cell.x, cell.y):
                return True
        return False

    def height(self):
        for y in range(depth - 1, -1, -1):
            if self.board[y] == 0:
                return depth - y - 1
        return depth

def decode_replay(replay_encoded):
    ret = ''
    for c in replay_encoded:
        if c in [' ', '\n', '\t']: 
            continue
        if (c >= '0' and c <='9') or (c >= 'A' and c <= 'F'):
            ret += moves[int(c, 16) / 4] + moves[int(c, 16) % 4]
        else:
            sys.stderr.write('invalid character in the replay! (%s)' % c)
            assert False
    return ret

def encode_replay(replay):
    tmp = ''
    for c in replay:
        if c in moves:
            tmp = tmp + c

    if len(tmp) % 2 == 1:
        tmp = tmp + 'D'

    ret = ''
    for i in range(0, len(tmp), 2):
        ret = ret + hex(moves.index(tmp[i]) * 4 + moves.index(tmp[i + 1]))[2].upper()
        if len(ret) % 5 == 4:
            ret += ' '

    return ret

def build_orientations():
    for piece in copy.copy(pieces_info):
        piece_info = copy.deepcopy(pieces_info[piece])
        pieces_info[piece + '0'] = piece_info

        for o in range(1, 4):
            new_piece_info = copy.deepcopy(piece_info)
            for cell_index in range(len(piece_info)):
                new_piece_info[cell_index]['x'] = 3 - piece_info[cell_index]['y']
                new_piece_info[cell_index]['y'] = piece_info[cell_index]['x']
            pieces_info[piece + str(o)] = new_piece_info
            piece_info = new_piece_info

# returns >=  0 if done and returns the new score (well modified)
#         == -1 if game over (well modified)
#         == -2 if OK and continue (piece_state modified)
#         == -3 if invalid move
def handle_move(well, piece_state, move):
    assert move in moves

    if move == 'L':
        piece_state.x = piece_state.x - 1
        if well.collision(piece_state):
            piece_state.x = piece_state.x + 1       # rollback
            return -3
        return -2
    elif move == 'R':
        piece_state.x = piece_state.x + 1
        if well.collision(piece_state):
            piece_state.x = piece_state.x - 1       # rollback
            return -3
        return -2
    elif move == 'D':
        piece_state.y = piece_state.y + 1
        if well.collision(piece_state):
            piece_state.y = piece_state.y - 1       # rollback
            return well.add(piece_state)            # return score or -1 if gameover
        return -2
    elif move == 'U':
        piece_state.o = (piece_state.o + 1) % 4
        if well.collision(piece_state):
            piece_state.o = (piece_state.o - 1) % 4 # rollback
            return -3
        return -2
    else:
        assert False

# Priority queue (highest score first)
class TaskQueue(object):
    def __init__(self):
        self.heap = []
        self.dict = {}

    def __len__(self):
        return len(self.heap)

    def add(self, well, score):
        if not well in self.dict or score > self.dict[well]:
            heapq.heappush(self.heap, (-score, well.height(), well))
            self.dict[well] = score

    def get(self):
        score, height, well = heapq.heappop(self.heap)
        score = -score
        height = height
        return score, height, well 

    def num_visited(self):
        return len(self.dict)

def best_height(well, piece, task_queue = None, current_score = 0):
    piece_state = PieceState(piece)
    trace = ''

    # little optimization skipping empty rows
    while piece_state.y + 4 < depth:
        if well.board[piece_state.y + 4] != 0:
            break
        piece_state.y = piece_state.y + 1
        trace += 'D'
        
    min_height = None

    queue = collections.deque()
    queue.append((piece_state, trace))

    visited = set()
    visited.add((piece_state.x, piece_state.y, piece_state.o))

    tmp_well = copy.deepcopy(well)
    while len(queue) > 0:
        piece_state, replay_so_far = queue.popleft()
        
        for move in moves:
            tmp_piece_state = copy.copy(piece_state)
            ret = handle_move(tmp_well, tmp_piece_state, move)

            if ret == -3:   # invalid move
                continue
            elif ret == -2: # continue
                if (tmp_piece_state.x, tmp_piece_state.y, tmp_piece_state.o) not in visited:
                    queue.append((tmp_piece_state, replay_so_far + move))
                    visited.add((tmp_piece_state.x, tmp_piece_state.y, tmp_piece_state.o))
            else:           # placed and/or gameover
                height = tmp_well.height()
                if min_height == None or min_height > height:
                    min_height = height
                if ret >= 0:
                    if task_queue is not None:
                        tmp_well.append_replay(replay_so_far + move)
                        task_queue.add(tmp_well, current_score + ret)
                tmp_well = copy.deepcopy(well)

    return min_height
                    
def worst_piece(well):
    max_height = None
    max_height_piece = None

    for piece in pieces_inorder:
        height = best_height(well, piece)
        if max_height== None or max_height < height:
            max_height = height
            max_height_piece = piece

    return max_height_piece
        
def replay_test(task_queue, seed):
    well = Well()
    piece_state = PieceState(worst_piece(well))
    score = 0
    pieces = 1

    for i, move in enumerate(seed):
        ret = handle_move(well, piece_state, move)
        if ret >= 0:
            well.dump()
            score += ret
            piece_state = PieceState(worst_piece(well))
            pieces = pieces + 1
            if task_queue is not None:
                tmp_well = copy.deepcopy(well)
                tmp_well.append_replay(seed[:i + 1])
                task_queue.add(tmp_well, score)
            print '%d/%d: score: %d (%d pieces)' % (i + 1, len(seed), score, pieces)
        elif ret == -1:
            break

def solve(hint_encoded = ''):
    task_queue = TaskQueue()
    replay_test(task_queue, decode_replay(hint_encoded))

    begin = time.time()
    trials = 0
    best_score = 0

    while len(task_queue) > 0:
        score, height, well = task_queue.get()
        trials = trials + 1
        if score > best_score:
            best_score = score
            replay = well.get_replay()

            print '(timestamp: %.3f, trial: %d) got a new best score %d!!' % \
                    (time.time() - begin, trials, best_score)

            print 'Replay:'
            print replay

            print 'Encoded replay:'
            print encode_replay(replay)

            well.dump()
            if score == 29:
                break

        if trials % 10 == 0:
            print '%dth trial, %d wells left,(%d seen)' % (trials, len(task_queue), task_queue.num_visited()), 
            print 'best score %d' % best_score, 
            print 'current score %d (height = %d)' % (score, height)

        if trials % 100 == 0:
            well.dump()

        next_piece = worst_piece(well)
        best_height(well, next_piece, task_queue, score)

    end = time.time()
    print 'total time =', end - begin

build_orientations()

if __name__ == '__main__':
    # prefiex (27 lines) of the best solution ever known (30 lines)
    sol30_encoded = '''C02A AAAA AAAB 00AA AAAA AC08 AAAA AAC2 AAAA AAAA C2AA AAAA AEAA AAAA AA56
    AAAA AAAA B55A AAAA AA96 AAAA AAAA D5AA AAAA A9AA AAAA AAB5 AAAA AAAA AAAA
    AAAA DAAA AAAA 9756 AAAA AA8A AAAA AAAB AAAA AAAB 5AAA AAAB 56AA AAAA AAAA
    A82A AAAA B00A AAAA A6D6 AB55 6AAA AAA9 4AAA AAA6 AAAA AD56 AAAA B56A AAAA
    032A AAAA A65B F00A AAAA AA6E EFC0 2AAA AAAA EB00 AAAA AAA8 0AAA AAAA 802A
    AAAA AA54 AAAA AAA1 AAAA AAA0 AAAA AAA0 0AAA AAAA C02A AAAA B002 AAAA B00A
    AAAC 2AAA AAB0 AAAA AEAA AAA9 5AAA AAA9 D5AA AAA5 AAAA AAB5 6AAA A6AA AAAB
    5AAA AAAA AAAA DAAA AAD5 56AA AA2A AAAA BAAA AAD6 AAAB 56AA AAAA 82AA AC02
    AAA7 B5AA D556 AAAA 52AA A6AA B55A AB56 AA80 FCAA AAA5 583F 0AAA A9BB BF00
    AAAA AE80 32AA AA82 FAAA A802 AAAA 96AA AA1A AAA8 2AAA A00A AAAB 00AA AB00
    AAB0 AAAB 0AAB AAA9 5AAA AD56 AA5A AAB5 6AAC 02A9 AAAB 5AAA AAAD AAB5 5AA2
    AAAE AA0A AAB2 AA'''

    solve(sol30_encoded)


# -----------------------------------

# vi: sts=4 et nocindent
