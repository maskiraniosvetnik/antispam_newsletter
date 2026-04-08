# antispam_newsletter
Newsletter sender based on python script

HowTo:

1. Enter your smtp host
2. Enter your desired port (skip if default)
3. Enter your email address 
4. Enter your desired display name
5. Enter your password (hidden)
6. Enter title
7. Enter email body (can support HTML) 
Finish with two blank lines (if html it has to be stripped of excess blank lines)
Pro tip: typing [user] in title or body automatically replaces "[user]" with loaded username per mail address 
8. Load bulk mailing list that looks like ↓

username:mail@example.mail
otheruser:somemail@mailme
anotheruser:anothermail@email.email
yetanotheruser:a@a.a

Pro tip if you dont want to send that email to some on that list you can "comment out" their details using "#" example ↓

#user:usermail.mail

↑ this recipient won't be on the list
