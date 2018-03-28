import numpy as np
import json_lines

class DataProcessor():
    """ The DataProcessor class handles reading data from file and 
        writing preprocessed data into a separate file
        embed data into vectors
    """
    def __init__(self):
        # Used for hashing gold labels into numeric format for training, omitting "-"
        self.GOLD_LABELS = {'entailment': 1, 'neutral': 0, 'contradiction': -1}
        self.GLOVE_MODEL_PATH = "models/glove.twitter.27B.200d.txt"
        self.EMBEDDING_DIM = 200
        self.glove_model = self.loadGloveModel(self.GLOVE_MODEL_PATH)
        self.HUNDRED_RAND_EMBEDDINGS = np.array([np.random.normal(0, 0.01, self.EMBEDDING_DIM)
            for i in range(100)])

    def get_batched_data(self, input_file_path, batch_size):
        """ Preprocess the data in a train/valid/test file into dictionaries that represent each batch
        Informations include:
            sentence1: an np array of batch_size x la (maximum) x
        Args:
            input_file_path: path to file where the input jsonl is
        Returns:
            embedded_data: a dictionary of dictionaries containing embeddings of 2 sentences and 
            their corresponding gold label in a numeric form
        """
        postprocessed_data = self.preprocess_jsonl(input_file_path, sentence_max_len=100)

        batch_array = np.array_split(postprocessed_data, len(postprocessed_data) / batch_size)
        for batch_dict in batch_array:
            batch_max_word_count1 = max([len(entry["sentence1"].split()) for entry in batch_dict])
            batch_max_word_count2 = max([len(entry["sentence2"].split()) for entry in batch_dict])
            embedded_data = {
                                "sentence1": np.array([self.gloVe_embeddings(entry["sentence1"],
                                    batch_max_word_count1) for entry in batch_dict]),
                                "sentence2": np.array([self.gloVe_embeddings(entry["sentence2"],
                                    batch_max_word_count2) for entry in batch_dict]),
                                "la": batch_max_word_count1,
                                "lb": batch_max_word_count2,
                                "gold_label": np.array([entry["gold_label"] for entry in batch_dict])
                            }
            yield embedded_data

    def preprocess_jsonl(self, input_file_path, sentence_max_len):
        """ handles reading data from input jsonl file and writing preprocessed data into a separate file
        Preprocessed data is in the json format: np array of {"sentence1":..., "sentence2":...,
        "gold_label": 1} semi sorted

        1. Extracting setences and gold label from jsonl file, removing instances with label "-" for
           gold label from the dataset
        2. Prepending each sentence with the NULL token
        3. Adding padding to the sentences to the maximum length
        4. Semi-sorting the data by length < 20, length < 50 and others (to ensure each batch has
           similar length)
        Args:
            input_file_path: path to file where the input jsonl is
            sentence_max_len: the length of the sentences we are adding padding to
        Returns:
            np array of new dictionayrs  {"sentence1":..., "sentence2":..., "gold_label": 1} semi sorted
        """
        short_data_list = []
        medium_data_list = []
        long_data_list = []

        with open(input_file_path, 'rb') as input_file: # opening file in binary(rb) mode    
            for item in json_lines.reader(input_file):
                if item["gold_label"] != "-": # Removing unlabeled data
                    new_item = {}
                    data_len = max(len(item["sentence1"]), len(item["sentence2"]))
                    # Prepending sentences with the NULL token
                    new_item["sentence1"] = self.pad_sentence('\0' + item["sentence1"], sentence_max_len) 
                    new_item["sentence2"] = self.pad_sentence('\0' + item["sentence2"], sentence_max_len)
                    new_item["gold_label"] = self.GOLD_LABELS[item["gold_label"]] # Converting gold label to numeric

                    if data_len < 20:
                        short_data_list.append(new_item)
                    elif data_len < 50:
                        medium_data_list.append(new_item)
                    else:
                        long_data_list.append(new_item)
            return np.concatenate((short_data_list, medium_data_list, long_data_list), axis=0)

    def loadGloveModel(self, glove_file_path):
        print("Loading Glove Model")
        model = {}
        with open(glove_file_path, 'r') as f:
            for line in f:
                splitLine = line.split()
                word = splitLine[0]
                embedding = np.array([float(val) for val in splitLine[1:]])
                model[word] = embedding
            print("Done.",len(model)," words loaded!")
            return model

    def gloVe_embeddings(self, sentence, max_word_count):
        """ Use 200 dimensional GloVe embeddings (Pennington et al., 2014) to represent words
        Normalize each vector to l2 norm of 1
        Out of Vocab words are hashed to random embedding
        Pad each sentence embedding to the max number of words in the batch

        Args:
            sentence: the string indicating the sentence we are making the embedding of
            max_word_count: 0th dimension of the returned embeddings, the sentence with the most words in this batch
        Returns:
            an np array of size #max_word_count x 200
        """
        words = sentence.split()
        num_words = len(words)

        assert num_words <= max_word_count

        # Embed each word, for previously unseen words, choose from the 100 random embeddings.
        word_embeddings = np.array([self.glove_model[word]
            if word in self.glove_model
            else self.HUNDRED_RAND_EMBEDDINGS[np.random.choice(len(self.HUNDRED_RAND_EMBEDDINGS))] for word in words])

        # If the 0th dimension != max_word_count, pad the embedding to the max word count in the batch
        if num_words < max_word_count:
            word_embeddings = np.append(word_embeddings, np.zeros((max_word_count - num_words, self.EMBEDDING_DIM)), axis=0)

        return word_embeddings

    def pad_sentence(self, sentence, sentence_max_len):
        """ Padding the input sentence to sentence_max_len with " ", which is masked out during training,
        take the first sentence_max_len characters if the number of chars in the sentences already exceeds sentence_max_len
        Args:
            sentence: string of sentence to be processed
            sentence_max_len: int indicating the largest number of chars a sentence can contain
        Returns:
            The padded sentence of sentence_max_len characters
        """
        if len(sentence) >= sentence_max_len:
            return sentence[0: sentence_max_len]

        return sentence.ljust(sentence_max_len)









