# Klang
## Abstract
The rise of social media means that the volume of microtexts has likewise increased by a significant amount. Identifying the topics of those microtexts is a difficult task. For longer texts there exists a plethora of techniques and algorithms, such as LDA. The existing and well known models fail on microtexts however due to their short length. Furthermore an important aspect of social media posts, the time of posting, is often ignored. It can be expected that posts made in succession share some or multiple common topics discussed therein. This is an aspect that is not well captured in existing topic detection and tracking architectures.\\
In this thesis I showcase two topic extraction algorithms, designed specifically for microtexts. One of them is the spIke algorithm. It can identify topics that have risen or dropped in popularity in a certain corpus compared to a reference corpus. One application of this, and the one that I will discuss in this thesis, is using it to compare social media posts on the platform Twitter (Tweets) made by a business school in a certain time frame to posts made by other, rival business schools, in the same time frame. This will allow us to find topics that are more more important for the first business school relative to other schools, in other words, their focus areas. The second algorithm is based on the tf-idf representation of documents and topics are extracted by clustering the documents into topic clusters and extracting the most indicative terms from the clusters.\\
I will then discuss the implementation of an algorithm that can infer hierarchies and relations between keywords that were used in tagging documents or even objects, called Klang. Klang is able to process temporal information, when each keyword is used in time, to create the relations between them. In this thesis I will describe the algorithm and examine topic hierarchies identified by it when applied to a corpus of Tweets made by business schools. This corpus is well-suited for our goal as there is a constant stream of new, short texts over a period of time. Each business school has a slightly different focus on the courses they teach which makes the corpus a good target to identify focus areas. The keywords found by both extraction algorithms are then used as input for the Klang algorithm and the resulting keyword relations and hierarchies found by it evaluated.

## Installation
Python 3.7 required.<br/>
It is suggested to follow the Django deployment guides:<br/>
[Deployment checklist](https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/)<br/>
[Deploy with wsgi](https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/)<br/>
Do not forget to check how to handle static files (Javascript and CSS):<br/>
[Managing static files (e.g. images, JavaScript, CSS)](https://docs.djangoproject.com/en/3.0/howto/static-files/)<br/>
The easiest way to handle the static files is to follow just this step:<br/>
[Deployment](https://docs.djangoproject.com/en/3.0/howto/static-files/#deployment)<br/>

Then, create and initialize the database, see the Django docs if you want to use a legacy database:<br/>
`python manage.py makemigrations`<br/>
`python manage.py migrate`<br/>
Then create a new superuser:<br/>
`python manage.py createsuperuser` and follow the instructions.<br/>


Alternatively you can select `all` and download all the resources.<br/>
As the directory for the resources, choose one that your server running the system can find. Using Apache2 on Ubuntu 14.04 for example, that would be `/var/www/nltk_data`. If you are unsure, refer to the documentation of your server or try to run the system and check the error message for the directories it searched to find the resources, then move them there.

## Usage
Continue reading for where to find the various algorithms and files required to run them.


### Klang algorithm
To run the Klang algorithm use `main.py` in the `klang` package.
Load suitable models, paths are provided, or generate one with spIke or tf-idf approach.
The raw inputs used in the thesis can be found in `klang_inputs_raw.zip`.


### spIke algorithm
To run the spIke algorithm see `thesis/spike_thesis.py`.
Includes the functions that were used to create the Klang inputs, for both spIke models and for tf-idf approach.

To use a general corpus the Wikipedia corpus of the University of Leipzig can be used.
You can download it here: https://wortschatz.uni-leipzig.de/de/download/german
The terms of use can be found here: https://wortschatz.uni-leipzig.de/de/usage

### tf-idf approach
Can be found in the package `cluster`.
`cluster_tweets.py` runs the entire pipeline of the approach and creates Klang output.


### Files

Files used in the creation of the thesis can be found here: https://drive.google.com/file/d/1AGnA7F9Ityi2fhSEWmGuHZXjIvcLMtW7/view?usp=sharing

### List of schools / consulting providers

The list of schools / consulting providers used for this thesis can be found in the file `RELEVANT.txt`.

### Documentation

The documentation can be found here: https://madjura.github.io/klang-thesis/

### Thesis files

The thesis in PDF format can be found here: https://github.com/Madjura/klang-thesis/blob/master/masters_thesis.zip .

The presentation of the thesis can be found here: https://github.com/Madjura/klang-thesis/blob/master/masters_thesis_presentation.zip .
