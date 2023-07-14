import lmql

@lmql.query
def test_beam_in():
    '''lmql
    beam(n=4)
        """English to French Translation:
        English: I am going to the store
        French: [word] [word] [word]
        """
    from 
        "random"
    where
        word in ["cat", "dog", "rabbit"]
    '''

if __name__ == "__main__":
    test_beam_in()