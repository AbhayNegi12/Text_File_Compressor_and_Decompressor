# huffman_compression.py
import heapq
from collections import defaultdict
from math import ceil

class Node:
    __slots__ = ("freq", "sym", "left", "right")
    def __init__(self, freq, sym=None, left=None, right=None):
        self.freq = freq
        self.sym = sym  
        self.left = left
        self.right = right
    def __lt__(self, other):
        return self.freq < other.freq

# ---------- bit helpers ----------
def bits_to_bytes(bits: str) -> bytes:
    if not bits:
        return b""
    pad = (-len(bits)) & 7 
    bits_padded = bits + ("0" * pad)
    out = bytearray()
    for i in range(0, len(bits_padded), 8):
        byte = bits_padded[i:i+8]
        out.append(int(byte, 2))
    return bytes(out)

def bytes_to_bits(b: bytes) -> str:
    return "".join(f"{byte:08b}" for byte in b)

# ---------- Huffman core on BYTES ----------
def build_huffman_tree(data: bytes):
    if not data:
        return None
    freq = defaultdict(int)
    for bt in data:
        freq[bt] += 1

    heap = [Node(f, sym=s) for s, f in freq.items()]
    heapq.heapify(heap)

    if len(heap) == 1:
        only = heap[0]
        return Node(only.freq, left=only)

    while len(heap) > 1:
        a = heapq.heappop(heap)
        b = heapq.heappop(heap)
        heapq.heappush(heap, Node(a.freq + b.freq, left=a, right=b))

    return heap[0]

def build_codes(node, prefix="", out=None):
    if out is None:
        out = {}
    if node is None:
        return out
    if node.sym is not None:
        out[node.sym] = prefix or "1"  
    else:
        build_codes(node.left, prefix + "0", out)
        build_codes(node.right, prefix + "1", out)
    return out

def serialize_header(original_size: int, codes: dict[int, str]) -> bytes:
    header = bytearray()
    header += b"HUF1"
    header += original_size.to_bytes(8, "big")
    header += len(codes).to_bytes(2, "big")

    for sym, code in codes.items():
        L = len(code)
        header.append(sym)                
        header.append(L & 0xFF)           
        code_bytes = bits_to_bytes(code)   
        header += code_bytes[:ceil(L/8)]  
    return bytes(header)

def parse_header(blob: bytes, offset=0):
    if blob[offset:offset+4] != b"HUF1":
        raise ValueError("Bad magic (not a HUF1 file).")
    offset += 4
    original_size = int.from_bytes(blob[offset:offset+8], "big"); offset += 8
    N = int.from_bytes(blob[offset:offset+2], "big"); offset += 2

    codes = {}
    for _ in range(N):
        sym = blob[offset]; offset += 1
        L = blob[offset]; offset += 1
        K = ceil(L/8)
        code_bytes = blob[offset:offset+K]; offset += K
        bits = bytes_to_bits(code_bytes)[:L]
        codes[sym] = bits

    pad_bits = blob[offset]; offset += 1
    return original_size, codes, pad_bits, offset

def rebuild_tree_from_codes(codes: dict[int, str]) -> Node:
    root = Node(0)
    for sym, code in codes.items():
        n = root
        for bit in code:
            if bit == "0":
                if n.left is None:
                    n.left = Node(0)
                n = n.left
            else:
                if n.right is None:
                    n.right = Node(0)
                n = n.right
        n.sym = sym
    return root

# ---------- public API ----------
def huffman_compress_bytes(data: bytes) -> tuple[bytes, int, int]:
    """Return (compressed_blob, original_bits, compressed_bits_true)."""
    if not data:
        header = b"HUF1" + (0).to_bytes(8, "big") + (0).to_bytes(2, "big") + bytes([0])
        return header, 0, 0

    root = build_huffman_tree(data)
    codes = build_codes(root)

    encoded_bits = "".join(codes[b] for b in data)
    data_bytes = bits_to_bytes(encoded_bits)
    pad_bits = (8 - (len(encoded_bits) % 8)) % 8

    header = serialize_header(len(data), codes)
    out = bytearray()
    out += header
    out.append(pad_bits) 
    out += data_bytes

    original_bits = len(data) * 8
    compressed_bits_true = len(encoded_bits)
    return bytes(out), original_bits, compressed_bits_true

def huffman_decompress_bytes(blob: bytes) -> bytes:
    if not blob:
        return b""
    original_size, codes, pad_bits, offset = parse_header(blob, 0)
    if offset >= len(blob):
        return b""
    data_bytes = blob[offset:]
    data_bits = bytes_to_bits(data_bytes)
    if pad_bits:
        data_bits = data_bits[:len(data_bits) - pad_bits]

    root = rebuild_tree_from_codes(codes)
    out = bytearray()
    n = root
    for bit in data_bits:
        n = n.left if bit == "0" else n.right
        if n.sym is not None:
            out.append(n.sym)
            n = root
            if len(out) == original_size: 
                break
    return bytes(out)
