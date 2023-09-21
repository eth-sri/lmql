INLINE_USE_PROMPT = """
Q: Mary had 5 apples. The next morning, she ate 2 apples. Then, in the afternoon, she bought as many apples as she had after eating those apples in the morning. How many apples did she end up with?
A: Let's think step by step.


Inline Tool Use:


Mary had 5 apples. 
After eating 2 apples in the morning, she had 5 apples - 2 apples <<calc("5-2") | 3 >> 3 apples left. 
In the afternoon, she bought as many apples as she had after eating those apples in the morning, so she bought 3 apples. 
Therefore, Mary ended up with 3 apples + 3 apples <<calc("3+3") | 6 >> 6 apples.





Q: Mario and Luigi together had 10 years of experience in soccer. Luigi had 3 more than Mario. How many did Mario have?
A: Let's think step by step.


Inline Tool Use:


Mario and Luigi together had 10 years of experience in soccer. 
Luigi had 3 more than Mario.
Therefore, Mario had (10 years - 3 years) divided by 2 <<calc("(10-3)/2") | 3.5 >> 3.5 years of experience.





Q: The planet Goob completes one revolution after every 2 weeks. How many hours will it take for it to complete half a revolution?
A: Let's think step by step.


Inline Tool Use:


We first compute the number of hours in a week 24 hours * 7 days <<calc("24*7") | 168 >> 168. 
Then, we compute the number of hours in a revolution 168 hours * 2 weeks <<calc 168*2 | 336 >> 336.
Finally, we compute the number of hours in half a revolution <<calc("336/2") | 168 >> 168.

"""