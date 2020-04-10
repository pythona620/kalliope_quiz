#!/usr/bin/env python

import sqlite3
import csv
import random
import string
import os
import textwrap

class DatabaseHandler(object):
  """Database interface. All DB calls are made in this class."""

  def __init__(self,dbcursor):
    self._cursor = dbcursor
    
  def get_question(self,questionid):
    """Return question text"""
    self._cursor.execute("SELECT questiontext FROM questions WHERE id=?",(questionid,))
    return self._cursor.fetchone()[0]
    
  def get_question_count(self):
    """Return total number of questions in DB"""
    self._cursor.execute("SELECT count(*) FROM questions");
    return self._cursor.fetchone()[0]
    
  def get_answers(self,questionid):
    """Return all possible answers for a given question"""
    self._cursor.execute("SELECT answertext,correct FROM answers WHERE questionid=?",(questionid,))
    return [{'answertext':answertext, 'correct':correct} for answertext,correct in self._cursor.fetchall()];
    
  def get_score(self,playerid):
    """Return score for a given player id"""
    self._cursor.execute("SELECT score FROM players WHERE id=?",(playerid,))
    return self._cursor.fetchone()[0]
    
  def set_score(self,playerid,score):
    """Set a player's score"""
    self._cursor.execute("UPDATE players SET score = ? WHERE id = ?",(score,playerid))
    self._cursor.connection.commit()
    
  def get_highscores(self,count=1):
    """Get top scores. Most recent entries are preferred in the event of a tie."""
    self._cursor.execute("SELECT id,name,score FROM players ORDER BY id DESC, id DESC LIMIT ?",(count,))
    return [{'id':id, 'name':name, 'score':score} for id,name,score in self._cursor.fetchall()];
    
  def create_player(self,name):
    """Add a player to the DB and return their unique ID"""
    self._cursor.execute("INSERT INTO players (name,score) VALUES (?,?)",(name,0))
    self._cursor.connection.commit()
    return self._cursor.lastrowid

  def check_db_ready(self):
    """check if the DB has been set up"""
    try:
      #note: this could also be done by querying the DB for tables by name, but this code is simpler
      self._cursor.execute("SELECT * FROM questions LIMIT 1")
      self._cursor.execute("SELECT * FROM answers LIMIT 1")
      self._cursor.execute("SELECT * FROM players LIMIT 1")
      return True
    except:
      return False

  def reset_db(self):
    """seed the database using accompanying CSV files"""
    c = self._cursor
    
    #drop tables
    for t in ["questions","answers","players"]:
      c.execute("DROP TABLE IF EXISTS " + t)

    #set up tables
    c.execute("CREATE TABLE questions (id INTEGER PRIMARY KEY, questiontext TEXT)")
    c.execute("CREATE TABLE answers (id INTEGER PRIMARY KEY, questionid INTEGER, answertext TEXT, correct INTEGER, FOREIGN KEY(questionid) REFERENCES questions(id))")
    c.execute("CREATE TABLE players (id INTEGER PRIMARY KEY, name TEXT, score INTEGER)")

    #import and insert seed data
    #questions
    with open("seeddata_questions.csv") as csvfile:
      dr = csv.DictReader(csvfile)
      insert_values = [(d['ID'],d['QuestionText']) for d in dr]

    c.executemany("INSERT INTO questions (id,questiontext) VALUES (?,?)", insert_values)

    #answers
    with open("seeddata_answers.csv") as csvfile:
      dr = csv.DictReader(csvfile)
      insert_values = [(d['ID'],d['QuestionID'],d['AnswerText'],d['Correct']) for d in dr]

    c.executemany("INSERT INTO answers (id,questionid,answertext,correct) VALUES (?,?,?,?)", insert_values)
    
    #players
    players = [(i,"Person "+chr(i+65),i+1) for i in range(5)]
    c.executemany("INSERT INTO players (id,name,score) VALUES (?,?,?)", players)

    c.connection.commit()


class Question(object):
  """Manages a question and its related answers"""

  def __init__(self,dbh,id):
    self._id = id
    self.questiontext = dbh.get_question(id)
    self.answers = dbh.get_answers(id)

  def get_question(self):
    """get the question text"""
    return self.questiontext
    
  def get_answers(self):
    """get a shuffled list of answers"""
    random.shuffle(self.answers)
    return self.answers

  def get_correct_answer_count(self):
    """get the number of correct answers for the given question"""
    return len([x for x in self.answers if x['correct']==1])
    
  def sanitize_user_answer_to_list(self,user_answer):
    """turn the user's response into a list of alphabetical characters"""
    # return [c for c in str.upper(user_answer) if c in string.uppercase]
    return [c for c in str.upper(user_answer) if c in string.ascii_uppercase]
        
  def check_answer(self,user_answer):
    """check correctness of user's response and whether a valid response was supplied.
    raises ValueError for invalid input, otherwise returns True/False"""

    user_answer = self.sanitize_user_answer_to_list(user_answer)
    ans_count = self.get_correct_answer_count()
    
    #check response validity
    if len(user_answer) == 0:
      raise ValueError("No answer selected")
    elif len(user_answer) != ans_count:
      raise ValueError("This question has " + str(ans_count) + " answer" + ("s" if ans_count>1 else ""))
      
    #loop through sanitized user response
    for ans in user_answer:
    
      #assign a numerical index so we can check against the list of answers
      answer_index = ord(ans) - ord('A')
      
      #check if the answer is within bounds of the answer list; raise an error if not
      if answer_index >= len(self.answers) or answer_index < 0:
        raise ValueError("Invalid selection: "+ans)
      
      #check if any user selections are wrong
      if self.answers[answer_index]['correct'] == 0:
        return False
    
    #if we make it out of the loop without triggering any returns or errors, the answer must be true
    return True

    
class Player(object):
  """Manages the current user and their score"""

  def __init__(self, dbh,name):
    self.id = dbh.create_player(name)
    self.name = name
    self._dbh = dbh
    self.score = 0
    
  def score_up(self,points=1):
    """increment the player's score"""
    newscore = self.score+points
    self._dbh.set_score(self.id,newscore)
    self.score = newscore
    
  def score_down(self,points=1):
    """decrement the player's score"""
    return self.score_up(self,-points)
  
  def get_score(self):
    """returns the player's current score"""
    return self.score
    
  def get_name(self):
    """return the player's name"""
    return self.name

  def get_id(self):
    """return the player's unique ID as set by the database"""
    return self.id

    
if __name__ == '__main__':    
  db = sqlite3.connect("quizapp.sqlite")
  dbh = DatabaseHandler(db.cursor())

  if not dbh.check_db_ready():
    print ("No database found. Initializing new database...")
    dbh.reset_db()
    print ("Done!\n")
  
  name = ""
  while name.strip() == "":
    name = input("Please enter your name: ")
  
  player = Player(dbh,name)
  
  qid = 0
  question_count = dbh.get_question_count()
  
  #loop through all the questions until we run out
  while (qid < question_count):
    os.system("cls" if os.name == "nt" else "clear")
    print (player.name + "                   Score: " + str(player.score))

    #create a question object and store some of the question's data
    question = Question(dbh,qid)
    answers = question.get_answers()
    answer_count = question.get_correct_answer_count()
    wrapper = textwrap.TextWrapper(initial_indent="    ",subsequent_indent="       ")
    
    #output the question and possible answers to the user
    print ("\n" + question.get_question() + "\n")
    print ("Select " + str(answer_count) + " answer" + ("s" if answer_count>1 else "") + " from below:\n")
    for i in range(len(answers)):
      anstext = chr(65+i) + ". " + answers[i]['answertext']
      for line in wrapper.wrap(anstext):
        print (line)
    
    #use a loop to repeatedly ask for answers if the user's input is invalid
    while True:
      try:
        #prompt the user for an answer
        user_answer = input("\nYour response ("+str(answer_count) + " answer" + ("s" if answer_count>1 else "")+"): ")

        #let the user know if they got it right
        if question.check_answer(user_answer):
          print ("Correct! You get "+str(answer_count)+" point"+("s" if answer_count>1 else ""),player.score_up(answer_count))
        else:
          print ("Sorry, that's incorrect. No points for you!")
        
        #exit the answer-asking loop
        break

      #something was wrong with the user's input. report the error and loop again
      except ValueError as e:
        print (e)

    #give the user a chance to see whether they got it right or not before proceeding
    # input("\nPress Enter to continue...")
    qid += 1

  #clear the screen
  os.system("cls" if os.name == "nt" else "clear")
  
  #report the player's final score
  print ("\nThanks for playing!")
  print ("\nFinal score: " + str(player.score))

  #report high scores
  print ("\nHigh scores:")
  rank = 0
  print ("  {0} {1} {2}".format("Rank","Pts","Name"))
  for hs_entry in dbh.get_highscores():
    rank += 1
    #include an indicator for the current player if they make the cut
    indic = "<------" if hs_entry['id'] == player.get_id() else ""
    print ("  {0:3d}. {1:3d} {2} {3}".format(rank, hs_entry['score'], hs_entry['name'], indic))

  db.close()