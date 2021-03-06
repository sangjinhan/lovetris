#!/usr/bin/env python

import sys
import copy
import collections
import time
import heapq
import random
import multiprocessing

bar = 4
width = 10
depth = 20

moves = ['L', 'R', 'D', 'U']

# workaround instead of OrderedDict
pieces_inorder = ['S', 'Z', 'O', 'I', 'L', 'J', 'T']
pieces_info = {
    'S': [
        (1, 2),
        (2, 1),
        (2, 2),
        (3, 1)
    ],
    'Z': [
        (1, 1),
        (2, 1),
        (2, 2),
        (3, 2)
    ],
    'O': [
        (1, 1),
        (1, 2),
        (2, 1),
        (2, 2)
    ],
    'I': [
        (0, 1),
        (1, 1),
        (2, 1),
        (3, 1)
    ],
    'L': [
        (1, 1),
        (1, 2),
        (2, 1),
        (3, 1)
    ],
    'J': [
        (1, 1),
        (1, 2),
        (1, 3),
        (2, 1)
    ],
    'T': [
        (1, 1),
        (2, 1),
        (2, 2),
        (3, 1)
    ]
}

class PieceState:
    def __init__(self, piece):
        self.piece = piece
        self.x = (width - 4) / 2
        self.y = 0
        self.o = 0

    def cells(self):
        return map(lambda cell: (self.x + cell[0], self.y + cell[1]),
                pieces_info[self.piece + str(self.o)])

class Well:
    def __init__(self, init_board_str = '', trace = '', parent = None):
        self.board = [0] * depth
        self.trace = trace
        self.parent = parent

        x = 0
        y = 0
        for c in init_board_str:
            if c in ':.#*':
                if c == '*':
                    self._set(x, y)
                
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
        for line in self.board:
            ret = (ret << width) | line
        return ret

    # returns True if the cell (x, y) in well is occupied
    def get(self, x, y):
        return (self.board[y] >> x) & 1 == 1

    # well is supposed to be immutable...
    def _set(self, x, y):
        self.board[y] = self.board[y] | (1 << x)

    def dump(self, piece_state = None):
        for y in range(depth):
            for x in range(width):
                c = '.'
                if y < bar:
                    c = ':'
                if piece_state != None:
                    for cell in piece_state.cells():
                        if x == cell[0] and y == cell[1]:
                            c = '#'
                if self.get(x, y):
                    c = '*'

                print c,
            print
        print '-' * (width * 2 - 1)
        print

    # returns the number of removed lines (0 if none, -1 if gameover)
    # and a child well (None if gameover)
    def add(self, piece_state, move_piece):
        # gameover check
        # Hatetris checks gameover first, then removes any complete lines.
        for cell in piece_state.cells():
            if cell[1] < bar:
                return -1, None

        child = Well(trace = move_piece, parent = self)
        child.board = copy.copy(self.board)

        for cell in piece_state.cells():
            child._set(cell[0], cell[1])

        # calculate score
        removed_lines = 0
        y = depth - 1
        while y >= 1:
            if child.board[y] == (1 << width) - 1:
                removed_lines += 1
                for y2 in range(y, 0, -1):
                    child.board[y2] = child.board[y2 - 1]
            else:
                y -= 1

        return removed_lines, child

    def get_trace(self):
        lineage = []
        p = self

        while p != None:
            if p.trace:
                lineage.append(p.trace)
            p = p.parent

        lineage.reverse()
        return ' '.join(lineage)

    def collision(self, piece_state):
        for cell in piece_state.cells():
            if cell[0] < 0 or cell[0] >= width:
                return True
            if cell[1] < 0 or cell[1] >= depth:
                return True
            if self.get(cell[0], cell[1]):
                return True
        return False

    def height(self):
        for y in range(depth - 1, -1, -1):
            if self.board[y] == 0:
                return depth - y - 1
        return depth

    popcount_table = [bin(num)[2:].count('1') for num in range(0, 2**width)]

    # returns the total number of cells in the well
    # Using this for the priority queue was a BAD idea....
    def num_cells(self):
        count = 0
        for line in self.board[bar:]:
            count += Well.popcount_table[line]
        return count

def decode_trace(trace_encoded):
    ret = ''
    for c in trace_encoded:
        if c in [' ', '\n', '\t']: 
            continue
        if (c >= '0' and c <='9') or (c >= 'A' and c <= 'F'):
            ret += moves[int(c, 16) / 4] + moves[int(c, 16) % 4]
        else:
            sys.stderr.write('invalid character in the trace! (%s)' % c)
            assert False
    return ret

def encode_trace(trace):
    tmp = ''
    for c in trace:
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
    def rotate(piece_info):
        ret = []
        for cell in piece_info:
            new_x = 3 - cell[1]
            new_y = cell[0]
            ret.append((new_x, new_y))
        return ret

    for piece in copy.copy(pieces_info):
        piece_info = pieces_info[piece]

        pieces_info[piece + '0'] = piece_info

        piece_info = rotate(piece_info)
        pieces_info[piece + '1'] = piece_info

        piece_info = rotate(piece_info)
        pieces_info[piece + '2'] = piece_info
        
        piece_info = rotate(piece_info)
        pieces_info[piece + '3'] = piece_info

# returns ==  0 if placed
#         == -2 if OK and continue (piece_state modified)
#         == -3 if invalid move
# piece_state may be modified.
def handle_move(well, piece_state, move):
    if move == 'L':
        piece_state.x -= 1
        if well.collision(piece_state):
            piece_state.x = piece_state.x + 1       # rollback
            return -3
        return -2
    elif move == 'R':
        piece_state.x += 1
        if well.collision(piece_state):
            piece_state.x = piece_state.x - 1       # rollback
            return -3
        return -2
    elif move == 'D':
        piece_state.y += + 1
        if well.collision(piece_state):
            # placed
            piece_state.y = piece_state.y - 1       # rollback
            return 0
        return -2
    elif move == 'U':
        # Do not allow rotation for 'O'. 
        # 'S', 'Z', 'I' pieces have some corner cases for this optimization.
        if piece_state.piece == 'O':
            return -2

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

def best_height(well, piece, children = None):
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

    while len(queue) > 0:
        original_piece_state, trace_so_far = queue.popleft()
        
        for move_single in moves:
            piece_state = copy.copy(original_piece_state)
            ret = handle_move(well, piece_state, move_single)

            if ret == -3:   # invalid move
                continue
            elif ret == -2: # continue
                if (piece_state.x, piece_state.y, piece_state.o) not in visited:
                    queue.append((piece_state, trace_so_far + move_single))
                    visited.add((piece_state.x, piece_state.y, piece_state.o))
            else:           # placed and/or gameover
                lines, child = well.add(piece_state, trace_so_far + move_single)

                if lines >= 0:
                    height = child.height()
                    if children is not None:
                        children.append((child, lines))
                else:
                    height = 9999       # gameover

                if min_height == None or min_height > height:
                    min_height = height

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
        
def replay_trace(trace = '', task_queue = None):
    well = Well()

    if task_queue is not None:
        task_queue.add(well, 0)     # add an empty well

    piece_state = PieceState(worst_piece(well))
    score = 0
    pieces = 1
    move_piece = ''

    for i, move in enumerate(trace):
        ret = handle_move(well, piece_state, move)
        move_piece += move

        if ret == 0:
            lines, child = well.add(piece_state, move_piece)
            if lines == -1:
                break

            score += lines
            pieces = pieces + 1
            print '%d/%d: score: %d (%d pieces)' % (i + 1, len(trace), score, pieces)

            well = child
            well.dump()

            piece_state = PieceState(worst_piece(well))
            move_piece = ''

            if task_queue is not None:
                task_queue.add(well, score)

def solve(hint_encoded = '', num_parallel_workers = 0):
    def worker(well):
        next_piece = worst_piece(well)
        children = []
        best_height(well, next_piece, children)
        for child, lines in children:
            child.parent = None
        return children

    task_queue = TaskQueue()
    replay_trace(decode_trace(hint_encoded), task_queue)

    trials = 0
    best_score = 0
    ties = 0

    begin = time.time()

    if num_parallel_workers > 0:
        pool = multiprocessing.Pool(processes = num_parallel_workers)
        pending_results = []

    while len(task_queue) > 0:
        score, height, well = task_queue.get()
        trials = trials + 1
        if score > best_score:
            best_score = score
            ties = 0

            print '(timestamp: %.2f, trial: %d) got a new best score %d!!' % \
                    (time.time() - begin, trials, best_score)

            trace = well.get_trace()
            print 'Trace:'
            print trace

            print 'Encoded trace:'
            print encode_trace(trace)

            print 'Dump:'
            well.dump()

            if best_score == 31:
                break

        elif score == best_score:
            ties += 1

        if trials % 100 == 0:
            print '%dth trial, %d wells left, %d seen,' % (trials, len(task_queue), task_queue.num_visited()), 
            print 'best score %d (%d ties)' % (best_score, ties),
            print 'current score %d (height = %d)' % (score, height)

        if num_parallel_workers > 0:
            pending_results.append((well, score, pool.apply_async(worker, args=(well,))))

            while len(pending_results) > 0 and \
                    (len(pending_results) >= num_parallel_workers * 2 or \
                     len(task_queue) == 0):
                well, score, async_result = pending_results.pop(0)

                children = async_result.get()                
                for child, lines in children:
                    child.parent = well
                    task_queue.add(child, score + lines)
        else:
            # sequential
            next_piece = worst_piece(well)
            children = []
            best_height(well, next_piece, children)

            for child, lines in children:
                task_queue.add(child, score + lines)

    end = time.time()
    print 'total time =', end - begin

build_orientations()

if __name__ == '__main__':
    # prefiex (27 lines) of the best solution
    sol27_encoded = '''C02A AAAA AAAB 00AA AAAA AC08 AAAA AAC2 AAAA AAAA C2AA AAAA AEAA AAAA AA56
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

    sol26_encoded = '''C02A AAAA AAAB 00AA AAAA AC08 AAAA AAC2 AAAA AAAA C2AA AAAA AEAA AAAA AA56 AAAA
    AAAA B55A AAAA AA96 AAAA AAAA D5AA AAAA A9AA AAAA AAB5 AAAA AAAA AAAA AAAA DAAA
    AAAA 9756 AAAA AA8A AAAA AAAB AAAA AAAB 5AAA AAAB 56AA AAAA AAAA A82A AAAA B00A
    AAAA A6D6 AB55 6AAA AAA9 4AAA AAA6 AAAA AD56 AAAA B56A AAAA 032A AAAA A65B F00A
    AAAA AA6E EFC0 2AAA AAAA EB00 AAAA AAA8 0AAA AAAA 802A AAAA AA54 AAAA AAA1 AAAA
    AAA0 AAAA AAA0 0AAA AAAA C02A AAAA B002 AAAA B00A AAAC 2AAA AAB0 AAAA AEAA AAA9
    5AAA AAA9 D5AA AAA5 AAAA AAB5 6AAA A6AA AAAB 5AAA AAAA AAAA DAAA AAD5 56AA AA2A
    AAAA BAAA AAD6 AAAB 56AA AAAA 82AA AC02 AAA7 B5AA D556 AAAA 52AA A6AA B55A AB56
    AA80 FCAA AAA5 583F 0AAA A9BB BF00 AAAA AE80 32AA AA82 FAAA A802 AAAA 96AA AA1A
    AAA8 2AAA A00A AAAB 00AA AB00 AAB0 AAAB 0AAB AAA9 5AAA AD56 AA5A AAB5 6AAC 02A9
    AAAB 5AAA AAAD AAB5 5AA2 AAAE AA'''

    sol21_encoded = '''C02A AAAA AAAB 00AA AAAA AC08 AAAA AAC2 AAAA AAAA C2AA AAAA AEAA AAAA AA56 AAAA
    AAAA B55A AAAA AA96 AAAA AAAA D5AA AAAA A9AA AAAA AAB5 AAAA AAAA AAAA AAAA DAAA
    AAAA 9756 AAAA AA8A AAAA AAAB AAAA AAAB 5AAA AAAB 56AA AAAA AAAA A82A AAAA B00A
    AAAA A6D6 AB55 6AAA AAA9 4AAA AAA6 AAAA AD56 AAAA B56A AAAA 032A AAAA A65B F00A
    AAAA AA6E EFC0 2AAA AAAA EB00 AAAA AAA8 0AAA AAAA 802A AAAA AA54 AAAA AAA1 AAAA
    AAA0 AAAA AAA0 0AAA AAAA C02A AAAA B002 AAAA B00A AAAC 2AAA AAB0 AAAA AEAA AAA9
    5AAA AAA9 D5AA AAA5 AAAA AAB5 6AAA A6AA AAAB 5AAA AAAA AAAA DAAA AAD5 56AA AA2A
    AAAA BAAA AAD6 AAAB 56AA AAAA 82AA AC02 AAA7 B5AA D556 AAAA 52AA A6AA B55A AB56
    AA80 FCAA AAA5 583F 0AAA A9BB BF00 AAAA AE80 32AA AA82 FAAA A802 AAAA 96AA AA1A
    AAA8 2AAA A'''

    solve(sol26_encoded, num_parallel_workers = 7)
