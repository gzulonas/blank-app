"""Reversing vowels in a string — two variants.

Version 1 (`reverseVowels`): the classic LeetCode 345 rule. Every single
vowel letter is movable, so each one is reversed against all the others.

Version 2 (`reverseSpokenVowels`): only *vowel clusters* — two or more
vowel letters in a row, i.e. the written form of a spoken diphthong such
as "ei", "ou", "eau" — are movable. A vowel standing alone between
consonants is left exactly where it is.
"""

VOWELS_EN = "aeiouAEIOU"
# Lithuanian also needs the diacritics and treats `y` as a vowel.
VOWELS_LT = "aeiouyąęėįųūAEIOUYĄĘĖĮŲŪ"


class Solution(object):

    # ---------------- Version 1: every vowel moves ----------------
    def reverseVowels(self, s):
        #Step 1: Define the set of vowels
        vowels = "aeiouAEIOU"

        #Step 2: Collect all vowels from the string
        collected_vowels = []
        for char in s:
            if char in vowels:
                collected_vowels.append(char)

        #Step 3: Reverse the list of collected vowels
        collected_vowels.reverse()

        #Step 4: Replace vowels in the original string
        result = []
        vowel_index = 0
        for char in s:
            if char in vowels:
                result.append(collected_vowels[vowel_index])
                vowel_index += 1
            else:
                result.append(char)
        return ''.join(result)

    # ---------------- Version 2: only clusters move ----------------
    def reverseSpokenVowels(self, s, vowels=VOWELS_EN, min_len=2):
        """Reverse only runs of `min_len`+ vowels; lone vowels stay put.

        A cluster keeps its own spelling and moves as one unit, so "ou"
        stays "ou" -- it just lands where another cluster used to be.
        """
        #Step 1: Find every maximal run of consecutive vowel letters
        runs = []
        i = 0
        n = len(s)
        while i < n:
            if s[i] in vowels:
                j = i
                while j < n and s[j] in vowels:
                    j += 1
                runs.append((i, j))
                i = j
            else:
                i += 1

        #Step 2: Keep only the clusters; a run of length 1 is a lone
        #        vowel, which is a positional marker and does not move
        clusters = [(a, b) for (a, b) in runs if b - a >= min_len]

        #Step 3: Reverse the order of the cluster texts
        texts = [s[a:b] for (a, b) in clusters]
        texts.reverse()

        #Step 4: Rebuild, dropping each cluster into the next slot
        result = []
        prev = 0
        for (a, b), text in zip(clusters, texts):
            result.append(s[prev:a])
            result.append(text)
            prev = b
        result.append(s[prev:])
        return ''.join(result)


if __name__ == "__main__":
    solution = Solution()
    samples = [
        "Autumn",
        "ICE",
        "beautiful house",
        "see you later",
        "road trip queue",
        "Hello, World!",
    ]
    print("%-18s %-18s %s" % ("input", "v1 (all vowels)", "v2 (clusters only)"))
    for text in samples:
        print("%-18s %-18s %s" % (
            text,
            solution.reverseVowels(text),
            solution.reverseSpokenVowels(text),
        ))
