from crewai import Agent, Task, Crew
import ollama
import smtplib
from email.mime.text import MIMEText
from feedback_system.database import get_connection
