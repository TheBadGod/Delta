from .util import HighestLookup, LowestLookup

class Codes:
    def __init__(self, num_codes, code_size, zero_inited):
        self.max_size = code_size
        
        self.codes = [0]*num_codes
        self.lengths = [0]*num_codes

        self.ResetLengths(zero_inited)
        self.CalculateCodes()
    
    def __str__(self):
        s = f"Codes <Length={len(self.codes)}, Codes={self.codes}, Lengths={self.lengths}>"
        return s

    def ResetLengths(self, zero_inited):
        if zero_inited:
            self.codes = [0]*len(self.codes)
        elif len(self.codes) < 3:
            self.codes = [1]*len(self.codes)
        else:
            length = len(self.codes)
            nbits = HighestLookup(length)
            start = 0
            self.codes = []

            if (1<<nbits) != len(self.codes):
                # first we have to use some nbits sized codes
                # but just so many that we get to a power of two when looking
                # at length-start
                # subtracting start does not really effect the target size
                # but it's done in the code
                target_size = (1<<(nbits+1)) - length - start
                self.codes += [nbits]*target_size
                start = (1<<(nbits+1)) - length
                
            # now its easy: just make all of them the same size
            self.codes += [nbits+1]*(length - start)

            assert len(self.codes) == length

    def CalculateCodes(self):
        # step 1: count frequencies
        frequencies = [0] * (self.max_size + 1)
        for i in self.codes:
            frequencies[i] += 1

        # step 2: check that for every codelength we have enough words available
        # starting at code length 1 with 2 words available (0/1)
        available = 2
        for length in range(1, self.max_size + 1):
            assert frequencies[length] <= available
            # in the next layer we have for every unused word 2 new ones
            available = 2 * (available - frequencies[length])

        # step 3: calculate how many codewords per layer are used to
        # go into the next layer
        used_per_layer = [0] * self.max_size
        value = 0
        for i in range(self.max_size - 1, -1, -1):
            used_per_layer[i] = value
            value = (frequencies[i] + value) // 2
        
        # step 4: calculate the codelengths and insert them in the table
        self.lengths = []
        for i in range(len(self.codes)):
            code_value = self.codes[i]
            if code_value == 0:
                # easy case: code 0 always has codelength 0
                self.lengths.append(0)
            else:
                # first take the next free index of a codeword at that layer
                # in the tree
                length = 0
                cv = used_per_layer[code_value]
                # reverse the bits of that index
                for m in range(code_value):
                    length = (length << 1) | (cv & 1)
                    cv >>= 1
                # insert it into the table as the length
                self.lengths.append(length)
                # and increment the counter for the layer
                used_per_layer[code_value] += 1


    def SetLengths(self, codes):
        assert len(codes) == len(self.codes)
        self.codes = codes
        self.CalculateCodes()

class DecoderTable:
    def __init__(self, codes):
        #print("Initializing table with", codes)
        
        masks = [0]*32

        current_max_lowest_bit = 0
        zero_index = len(codes.codes)

        # go through each code size value
        for i, (size, code) in enumerate(zip(codes.lengths, codes.codes)):
            if code and size:
                lowest_bit = LowestLookup(size)
                # generate a mask for bits which would be zero
                mask = code - lowest_bit - 1
                current_max_lowest_bit = max(current_max_lowest_bit, lowest_bit)

                if masks[lowest_bit] < mask:
                    masks[lowest_bit] = mask

            if code and not size:
                zero_index = i

        nbits = current_max_lowest_bit
        table_size = 0
        for x in range(nbits+1):
            table_size += 1<<masks[x]

        # +1 for the extra 0 in the beginning
        table_size = (table_size + 1)

        # fill in the small codewords' offset and masks
        self.offsets = []
        self.masks = []

        offset = 0
        for i in range(nbits+1):
            n = 1 << masks[i]
            self.offsets.append(offset)
            self.masks.append(n-1)
            offset += n

        # fill in the remaining (to fill up to 32)
        for i in range(nbits+1, 32):
            self.offsets.append(offset)
            self.masks.append(0)
        
        # now onto decoding the values
        self.values = [0]*table_size

        # some weird check here to fill the array with nulls...
        # but since i initialize them to 0 anyway i don't care

        # time to fill the values table
        for value, (size, code) in enumerate(zip(codes.lengths, codes.codes)):
            if size:
                idx = LowestLookup(size)
                mask = code - idx - 1
                pos = self.offsets[idx] + (size >> (idx + 1))
                extra_bit = (1 << mask) 
                num_words = 1 << (masks[idx] - mask)
                for i in range(num_words):
                    self.values[pos] = value
                    pos = pos + extra_bit

        if current_max_lowest_bit < len(codes.codes):
            self.values[-1] = zero_index

        self.lengths = codes.codes

    def __str__(self):
        return f"""DecoderTable <Values={self.values}>"""

    def Read(self, bs):
        N = bs.p(32) | (1 << 31)
        size = LowestLookup(N)
        offset = self.offsets[size]
        mask = self.masks[size]
        value_index = ((N>>(size + 1)) & mask) + offset
        value = self.values[value_index]
        bs.r(self.lengths[value])
        return value

