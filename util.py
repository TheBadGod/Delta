# Helper functions which determine the lowest / highest set bit
# i don't know the math behind these (i guess just the fact that mod 37)
# gives us a nice value in small range which is unique for all possible
# values after setting all the bits above the lowest bit

HighestLUT = [32,0,25,1,22,26,31,2,15,23,29,27,10,32,12,3,6,16,32,24,21,30,14,28,9,11,5,32,20,13,8,4,19,7,18,17,32]

def HighestLookup(n):
    # the shifting will figure out which is the highest set bit
    # not quite sure how they figure out the index by that
    n |= n >> 1
    n |= n >> 2
    n |= n >> 4
    n |= n >> 8
    n |= n >> 16
    n %= 0x25
    return HighestLUT[n]

LowestLUT = [32,27,23,2,26,1,0,32,18,19,8,20,5,9,14,21,32,6,12,10,29,15,31,22,25,32,17,7,4,13,32,11,28,30,24,16,3]

def LowestLookup(n):
    n |= n<<1
    n |= n<<2
    n |= n<<4
    n |= n<<8
    n |= n<<16
    n &= (2**32-1)
    n %= 0x25
    return LowestLUT[n]
