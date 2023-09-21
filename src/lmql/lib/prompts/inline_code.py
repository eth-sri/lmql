INLINE_CODE_PROMPT = '''
Q: Mary had 5 apples. The next morning, she ate 2 apples. Then, in the afternoon, she bought as many apples as she had after eating those apples in the morning. How many apples did she end up with?

# solution in Python:


def solution():
    """Mary had 5 apples. The next morning, she ate 2 apples. Then, in the afternoon, she bought as many apples as she had after eating those apples in the morning. How many apples did she end up with?"""
    apple_initial = 5 #| 5
    apple_eaten = 2 #| 2
    apple_left = apple_initial - apple_eaten #| 3
    apple_bought = apple_left #| 3
    result = apple_left + apple_bought #| 6
    return result #| 6





Q: Mario and Luigi together had 10 years of experience in soccer. Luigi had 3 more than Mario. How many did Mario have?

# solution in Python:


def solution():
    """Mario and Luigi together had 10 years of experience in soccer. Luigi had 3 more than Mario. How many did Mario have?"""
    mario_experience = (10 - 3)/2 #| 3.5
    result = mario_experience #| 3.5
    return result #| 3.5





Q: The planet Goob completes one revolution after every 2 weeks. How many hours will it take for it to complete half a revolution?

# solution in Python:


def solution():
    """The planet Goob completes one revolution after every 2 weeks. How many hours will it take for it to complete half a revolution?"""
    one_revolution_week = 2 #| 2
    half_revolution_week = one_revolution_week/2 #| 1.0
    half_revolution_hour = half_revolution_week * 7 * 24 #| 168.0
    result = half_revolution_hour #| 168.0
    return result #| 168.0





'''.strip()