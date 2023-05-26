PROMPT = """
Q: Mary had 5 apples. The next morning, she ate 2 apples. Then, in the afternoon, she bought as many apples as she had after eating those apples in the morning. How many apples did she end up with?
A: Let's think step by step.


Inline Tool Use:


Mary had 5 apples
    apples(mary) is 5
The next morning, she ate 2 apples.
    eats_apples(mary, 2, morning)
    now mary has 5 apples - 2 apples <<calc("5-2") | 3 >> 3
Then, in the afternoon, she bought as many apples as she had after eating those apples in the morning.
    afternoon: mary buys apples like she had in morning
    thus buys(mary, apples, 3)
How many apples did she end up with?
    now marry has 3 apples + 3 apples <<calc("3+3") | 6 >> 6





Q: Mario and Luigi together had 10 years of experience in soccer. Luigi had 3 more than Mario. How many did Mario have?
A: Let's think step by step.


Inline Tool Use:


Mario and Luigi together had 10 years of experience in soccer
    experience(mario + luigi) is 10
Luigi had 3 more than Mario.
    experience(luigi) is experience(mario) + 3
How many did Mario have?
    thus experience(mario) = (10 years - 3 years) divided by 2 <<calc("(10-3)/2") | 3.5 >> 3.5





Q: The planet Goob completes one revolution after every 2 weeks. How many hours will it take for it to complete half a revolution?
A: Let's think step by step.


Inline Tool Use:

Preliminary:
    hours(week) is 24 hours * 7 days <<calc("24*7") | 168 >> 168
one revolution after every 2 weeks:
    hours(revolution) is 168 hours * 2 weeks <<calc 168*2 | 336 >> 336
How many hours will it take for it to complete half a revolution?
    thus hours(half a revolution) is <<calc("336/2") | 168 >> 168

"""