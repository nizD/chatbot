#building chatbot with DeepNLP
#importing libraries

import numpy as np
import tensorflow as tf
import re
import time


#importing dataset
lines = open("movie_lines.txt",encoding='utf-8',errors='ignore').read().split('\n')
conversations=open("movie_conversations.txt",encoding='utf-8',errors='ignore').read().split('\n')

#PART 1 DATA PREPROCESSING AND NLP

#creating a dictionary that maps each line in to its id
id2line = {}
for line in lines:
    _line=line.split(' +++$+++ ')
    if len(_line) == 5:
        id2line[_line[0]]=_line[4]
        
        
#creating a list of conversation
conversations_ids = []
for conversation in conversations[:-1]:
    _conversation=conversation.split(' +++$+++ ')[-1][1:-1].replace("\'","").replace(" ","")
    conversations_ids.append(_conversation.split(","))
    
#getting seperately the question and the answer
questions=[]
answers=[]

for conversation in conversations_ids:
    for i in range(len(conversation)-1):
        questions.append(id2line[conversation[i]])
        answers.append(id2line[conversation[i+1]])   

#doing first cleaning of the text
def clean_text(text):
    text=text.lower()
    text=re.sub(r"he's","he is",text)
    text=re.sub(r"she's","she is",text)
    text=re.sub(r"that's","that is",text)
    text=re.sub(r"what's","what is",text)
    text=re.sub(r"where's","where is",text)
    text=re.sub(r"i'm","i am",text)
    text=re.sub(r"\'ll"," will",text)
    text=re.sub(r"\'ve"," have",text)
    text=re.sub(r"\'re"," are",text)
    text=re.sub(r"\'d"," would",text)
    text=re.sub(r"won't","will not",text)
    text=re.sub(r"can't","can not",text)
    text=re.sub(r"[-+*/()<>\"&%$#^~|.,?=]","",text)
    return text

#cleaning the question and answer
clean_question=[]
for question in questions:
    clean_question.append(clean_text(question))

clean_answer=[]    
for answer in answers:
    clean_answer.append(clean_text(answer))

#creating a dictionary that maps each word to its number of occurence
word2count ={}
for question in clean_question:
    for word in question.split():
        if word not in word2count:
            word2count[word]=1
        else:
            word2count[word] +=1
            
for answer in clean_answer:
    for word in answer.split():
        if word not in word2count:
            word2count[word]=1
        else:
            word2count[word] +=1

#creating two dictionaries to uniquely map the clean question and clean answer words
threshold = 20
questionwords2int = {}
word_number = 0
for word,count in word2count.items():
    if count >= threshold:
        questionwords2int[word]=word_number
        word_number += 1
        
answerwords2int = {}
word_number=0
for word,count in word2count.items():
    if count >= threshold:
        answerwords2int[word]=word_number
        word_number += 1

#adding last token to the two dictionaries
tokens =['<PAD>','<EOS>','<OUT>','<SOS>']
for token in tokens:
    questionwords2int[token]=len(questionwords2int)+1
    
for token in tokens:
    answerwords2int[token]=len(answerwords2int)+1
    
#creating inverse dictionary of answerwords2int
answerint2word={w_i:w for w,w_i in answerwords2int.items()}

#adding <EOS> to the end of all the answer
for i in range(len(clean_answer)):
    clean_answer[i] += " <EOS>"
    
#translatin all the question and answer in to integer
#replacing all the words that we filtered out by <OUT>
questions_into_int =[]
for question in clean_question:
    ints=[]
    for word in question.split():
        if word not in questionwords2int:
            ints.append(questionwords2int['<OUT>'])
        else:
            ints.append(questionwords2int[word])
    
    questions_into_int.append(ints)
    
answers_into_int = []
for answer in clean_answer:
    ints=[]
    for word in answer.split():
        if word not in answerwords2int:
            ints.append(answerwords2int['<OUT>'])
        else:
            ints.append(answerwords2int[word])
    
    answers_into_int.append(ints)
    
#sorting the question by their lengths
sorted_clean_question =[]
sorted_clean_answer =[]
for length in range(1,25+1):
    for  i in enumerate(questions_into_int):
        if len(i[1]) == length:
            sorted_clean_question.append(questions_into_int[i[0]])
            sorted_clean_answer.append(answers_into_int[i[0]])
            
#END OF DATA PREPROCESSING AND NLP

#PART 2 - BUILDING THE SEQ2SEQ MODEL

#creating a placeholders for the input and the target
def model_input():
    inputs = tf.placeholder(tf.int32,[None,None],name='input')
    targets = tf.placeholder(tf.int32,[None,None],name='target')
    lr = tf.placeholder(tf.float32,name='learning_rate')
    keep_prob = tf.placeholder(tf.float32,name='keep_prob')
    
    return inputs,targets,lr,keep_prob


#creating a preprocessed targets
def preprocess_targets(targets,word2int,batch_size):
    left_side = tf.fill([batch_size,1],word2int['<EOS>'])
    right_side = tf.strided_slice(targets,[0,0],[batch_size,-1],[1,1])
    preprocessed_targets = tf.concat([left_side,right_side],1)


    return preprocessed_targets
    
            
#creating the encoder rnn layer
def encoder_rnn(rnn_inputs,rnn_size,num_layers,keep_prob,sequence_length):
    lstm=tf.contrib.rnn.BasicLSTMCell(rnn_size)
    lstm_dropout = tf.contrib.rnn.DropoutWrapper(lstm,input_keep_prob=keep_prob)
    encoder_cell = tf.contrib.rnn.MultiRNNCell([lstm_dropout]*num_layers)
    encoder_state = tf.nn.bidirectional_dynamic_rnn(cell_fw=encoder_cell,cell_bw=encoder_cell,
                                                    sequence_length = sequence_length,inputs=rnn_inputs,
                                                    dtype=tf.float32)
    return encoder_state

#decoding the training set
def decode_training_set(encoder_state,decoder_cell,decoder_embedded_input,sequence_length
                        ,decoding_scope,output_function,keep_prob,batch_size):
    attention_states = tf.zeros([batch_size,1,decoder_cell.output_size])
    attention_key,attention_values,attention_score_function,attention_construct_function = tf.contrib.seq2seq.prepare_attention(attention_states,attention_option='bahdanau',num_units = decoder_cell.output_size)
    training_decoder_function = tf.contrib.seq2seq.attention_decoder_fn_train(encoder_state[0],attention_key,attention_values,attention_score_function,attention_construct_function,name='attn_dec_train')
    decoder_output,decoder_final_state,decoder_final_context_state = tf.contrib.seq2seq.dynamic_rnn_decoder(decoder_cell,training_decoder_function,decoder_embedded_input,sequence_length,decoding_scope)
    decoder_output_dropout = tf.nn.dropout(decoder_output,keep_prob)
    
    return output_function(decoder_output_dropout)

#decoding the test/validation set
def decode_test_set(encoder_state,decoder_cell,decoder_embedding_matrix,sos_id,eos_id,maximum_length,
                    num_words,sequence_length,decoding_scope,output_function,keep_prob,batch_size):
    attention_states = tf.zeros([batch_size,1,decoder_cell.output_size])
    attention_key,attention_values,attention_score_function,attention_construct_function=tf.contrib.seq2seq.prepare_attention(attention_states,
                                                                                                                              attention_option = 'bahdanau',
                                                                                                                              num_units =decoder_cell.output_size)
    test_decoder_function = tf.contrib.seq2seq.attention_decoder_fn_inference(output_function,
                                                                              encoder_state[0],
                                                                              attention_key,
                                                                              attention_values,
                                                                              attention_score_function,
                                                                              attention_construct_function,
                                                                              decoder_embedding_matrix,
                                                                              sos_id,
                                                                              eos_id,
                                                                              maximum_length,
                                                                              num_words,
                                                                              name = 'attn_dec_inf'
                                                                              )
    test_predictions,decoder_final_state,decoder_final_context_state = tf.contrib.seq2seq.dynamic_rnn_decoder(decoder_cell,
                                                                                                              test_decoder_function,
                                                                                                              scope=decoding_scope)
    
    return test_predictions

#creating the decoder rnn layer
def decoder_rnn(decoder_embedded_input,decoder_embedding_matrix,encoder_state,num_words,sequence_length,rnn_size,num_layers,word2int,keep_prob,batch_size):
    with tf.variable_scope("decoding") as decoding_scope:
        lstm = tf.contrib.rnn.BasicLSTMCell(rnn_size)
        lstm_dropout = tf.contrib.rnn.DropoutWrapper(lstm,input_keep_prob = keep_prob)
        decoder_cell = tf.contrib.rnn.MultiRNNCell([lstm_dropout]*num_layers)   #creating multistacked lstm
        weights = tf.truncated_normal_initializer(stddev=1.0)
        biases = tf.zeros_initializer()
        output_function = lambda x : tf.contrib.layers.fully_connected(x,
                                                                       num_words,
                                                                       None,
                                                                       scope = decoding_scope,
                                                                       weights_initializer = weights,
                                                                       biases_initializer = biases)    #creating the fully connected output layer
        training_predictions = decode_training_set(encoder_state,
                                                   decoder_cell,
                                                   decoder_embedded_input,
                                                   sequence_length,
                                                   decoding_scope,
                                                   output_function,
                                                   keep_prob,
                                                   batch_size)
        decoding_scope.reuse_variables()
        test_predictions = decode_test_set(encoder_state,
                                           decoder_cell,
                                           decoder_embedding_matrix,
                                           word2int['<SOS>'],
                                           word2int["<EOS>"],
                                           sequence_length - 1,
                                           num_words,
                                           decoding_scope,
                                           output_function,
                                           keep_prob,
                                           batch_size)
        
        
    return training_predictions,test_predictions


#building the seq2seq model
def seq2seq_model(inputs,targets,keep_prob,batch_size,sequence_length,answer_num_words
                  ,question_num_words,encoder_embedding_size,decoder_embedding_size,rnn_size
                  ,num_layers,questionwords2int):
    encoder_embedded_input = tf.contrib.layers.embed_sequence(inputs,
                                                              answer_num_words+1,
                                                              encoder_embedding_size,
                                                              initializer=tf.random_uniform_initializer(0,1))
    encoder_state = encoder_rnn(encoder_embedded_input,rnn_size,num_layers,keep_prob,sequence_length)
    preprocessed_targets = preprocess_targets(targets,questionwords2int,batch_size)
    decoder_embedding_matrix = tf.Variable(tf.random_uniform_initializer([question_num_words + 1,decoder_embedding_size],0,1))
    decoder_embedded_input = tf.nn.embedding_lookup(decoder_embedding_matrix,preprocessed_targets)
    training_predictions,test_predictions = decoder_rnn(decoder_embedded_input,
                                                        decoder_embedding_matrix,
                                                        encoder_state,
                                                        question_num_words,
                                                        sequence_length,rnn_size,
                                                        num_layers,
                                                        questionwords2int,
                                                        keep_prob,
                                                        batch_size)
    return training_predictions,test_predictions

    

#PART3 TRAINING THE SEQ2SEQ MODEL

#settinh the hyperparameter
epoch =100
batch_size = 64
rnn_size = 512
num_layers = 3
encoding_embedding_size = 512
decoding_embedding_size = 512
learning_rate = 0.01
learning_rate_decay = 0.9
min_learning_rate = 0.0001
keep_probability = 0.5

#defining a session
tf.reset_default_graph()
session =tf.InteractiveSession()

#loading the model input
inputs,targets,lr,keep_prob = model_input()

#setting the sequence length
sequence_length = tf.placeholder_with_default(25,None,name = 'sequence_length')

#getting the shape of the input tensor
input_shape = tf.shape(inputs)


# Getting the training and test predictions
training_predictions, test_predictions = seq2seq_model(tf.reverse(inputs, [-1]),
                                                       targets,
                                                       keep_prob,
                                                       batch_size,
                                                       sequence_length,
                                                       len(answerwords2int),
                                                       len(questionwords2int),
                                                       encoding_embedding_size,
                                                       decoding_embedding_size,
                                                       rnn_size,
                                                       num_layers,
                                                       questionswords2int)
    
        
        





    
    












