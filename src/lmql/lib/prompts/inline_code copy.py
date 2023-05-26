INLINE_CODE_PROMPT = '''
Q: Mary had 5 apples. The next morning, she ate 2 apples. Then, in the afternoon, she bought as many apples as she had after eating those apples in the morning. How many apples did she end up with?

# solution in Python:


# Mary had 5 apples. 
apple_initial = 5 #| 5
# The next morning, she ate 2 apples. (in apples)
apple_eaten = 2 #| 2
apple_left = apple_initial - apple_eaten #| 3
# Then, in the afternoon, she bought as many apples as she had after eating those apples in the morning. (in apples)
apple_bought = apple_left #| 3
# How many apples did she end up with? (in apples)
result = apple_left + apple_bought #| 6
print(result) #| 6





Q: Mario and Luigi together had 10 years of experience in soccer. Luigi had 3 more than Mario. How many did Mario have?

# solution in Python:


# Mario and Luigi together had 10 years of experience in soccer. (in years)
mario_and_luigi_experience = 10 #| 10
luigi_more = 3 #| 3
equal_experience = mario_and_luigi_experience - luigi_more #| 7
# Luigi had 3 more than Mario. (in years)
mario_experience = equal_experience / 2 #| 3.5
result = mario_experience
print(result) #| 3.5





Q: The planet Goob completes one revolution after every 2 weeks. How many hours will it take for it to complete half a revolution?

# solution in Python:


# The planet Goob completes one revolution after every 2 weeks. (in weeks)
one_revolution_week = 2 #| 2
# half a revolution would be  (in weeks)
half_revolution_week = one_revolution_week/2 #| 1
# in hours it will take (in hours)
half_revolution_hour = half_revolution_week * 7 * 24 #| 168
result = half_revolution_hour
print(result) #| 168






'''.strip() + '\n' * 7