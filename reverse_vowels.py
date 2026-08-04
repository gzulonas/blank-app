class Solution(object):
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


#Test Case
solution = Solution()
print(solution.reverseVowels("Autumn"))
