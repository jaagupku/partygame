Party game is a quiz/trivia type of game that is played by showing the questions
on a big main screens and players use their phones to play the game.

The game sets are defined in json files.

When defining a game it has option to include host role.
The host role does not answer the questions but instead uses their phone
to:
1. Start the game
2. Go to the next question
3. Award points to player
4. etc, in summary controls the game flow like a tv show host.

The questions can have different elements:
1. Title text: Large, suitable for just simple questions
2. Small text: Description, explanation. It can add additional context to the question
3. Image: Question could be about image.
   1. Image should also have different reveal possibilities:
      1. None: Image is just shown
      2. Blur to clear. Image starts off blurry and clears up in the amount of time that is defined in question
      3. Blur with circle: Image is blurred, but a small circle is bouncing around lika a DVD screensaver. The circle gets slowly larger and displaying more image overtime. The whole image is revealed after configured amount of time
      4. Zoom: Image starts very zoomed in to random point and slowly zooms out.
4. Audio: For example guess the sound or song.
5. Video: Displays a short video. Configured if shows single time or is looping

It should also be possible to configure how much time players have to answer the question.
Time for each question can also be configured to be enforced by a system or not.
For example if it is not enforced by system, then on main screen it displays the time but after it reaches zero, it does not proceed to next state.

Players answering on their phone:
For each question it can also be specified what is the input displayed to the players on their phones.

Inputs can be:
1. Buzzer: (Available only on host run games) - When question is displayed, then buzzers on phones are activated. The player who clicked on their button first gets to answer in real life. The host can choose on their device weather to accept it and how many points to award.
2. Text: Players type answer.
   1. Host run option: show answers to host on hosts phone and host can choose to display answer on main screen, accept answers, award points to players.
   2. Without host player: On question correct answers are also included and the system automatically awards configured amount of points to players who answered correctly
3. Number: Similar to text input.
   1. Can also have option to be a slider if it has min and max values set.
4. Ordering: users have multiple options on their phone and have to set them in some specific order.
   1. The answers are evaluated automatically by system and not by host.
5. None: This can be used for just simple "slides" or transistioning texts on main screen. For example "Category: Music" or "Now we get to harder questions! Good luck!"


When the game is created on main screen, then there can be selected if there is host player or not. If no host players are available, then buzzer quetsions are skipped and automatic evaluation is used for other questions. All questions require having answers in the game files and if host player is active, then they can see the correct answers on their phones.
