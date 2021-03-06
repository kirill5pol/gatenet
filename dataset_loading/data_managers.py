import os
import numpy as np
import time
from PIL import Image
import matplotlib.pyplot as plt
from dataset_loading.datasets import *

"""
# general class to handle dataset operations
class DataManager:

    def __init__(self, dataset='tiny-imagenet', load_images_in_memory=False):

        if dataset == 'mnist':
            self.path = "../datasets/mnist"
        elif dataset == 'omniglot':
            self.path = "../datasets/omniglot"
        elif dataset == 'tiny-imagenet':
            self.path = "../datasets/tiny-imagenet"
        elif dataset == 'mini-imagenet':
            self.path = "../datasets/mini-imagenet"
            self.label_type = np.int32
        elif dataset == 'simple-linear':
            self.path = "../datasets/simple_linear"
            self.label_type = np.float32

        # load specific dataset class
        self.dataset = load_dataset(self.path, dataset, load_images_in_memory)

        # get information about dataset
        self.train_classes = self.dataset.train_classes
        self.val_classes = self.dataset.val_classes
        self.test_classes = self.dataset.test_classes

        self.images_per_class = self.dataset.images_per_class
        self.image_size = self.dataset.image_size

    def build_dataset(self):
        raise NotImplementedError()

    def get_train_batch(self, meta_type='train'):
        raise NotImplementedError()

    def get_test_batch(self, meta_type='train'):
        raise NotImplementedError()

    def _meta_train_get_train_batch(self):
        raise NotImplementedError()

    def _meta_train_get_test_batch(self):
        raise NotImplementedError()

    def _meta_val_get_train_batch(self):
        raise NotImplementedError()

    def _meta_val_get_test_batch(self):
        raise NotImplementedError()

    def _meta_test_get_train_batch(self):
        raise NotImplementedError()

    def _meta_test_get_test_batch(self):
        raise NotImplementedError()


# Specific class to handle meta-dataset operations
class MetaDataManager(DataManager):
    def __init__(self,
                 dataset='tiny-imagenet',
                 load_images_in_memory=False,
                 seed=0,
                 splits={'train':0.7, 'val':0.15, 'test':0.15}):
        super(MetaDataManager, self).__init__(dataset, load_images_in_memory)

        # Set random seed (optional)
        if seed is not None:
            np.random.seed(seed)

        # Shuffle the indices of the classes
        shuffled_classes = np.arange(self.classes)
        np.random.shuffle(shuffled_classes)

        train_len = int(splits['train'] * self.classes)
        val_len = int(splits['val'] * self.classes)

        # Create the splits for train, val, & test
        self.classes_tr = shuffled_classes[0:train_len]
        self.classes_val = shuffled_classes[train_len:train_len+val_len]
        self.classes_ts = shuffled_classes[train_len+val_len:]

    ##### Build the datasets ###################################################
    def _build_dataset_helper(self, _classes, num_dataset_classes=5, k_shot=5, dataset_num_test=5):
        self.k_shot = k_shot
        self.num_dataset_classes = num_dataset_classes
        self.dataset_num_test = dataset_num_test
        dataset_num_train = self.images_per_class - dataset_num_test

        # Pick classes for dataset
        self.dataset_classes = np.random.choice(_classes, num_dataset_classes, replace=False)

        # Pick images for dataset
        dataset_train_images = np.empty((num_dataset_classes, dataset_num_train), dtype=np.uint8)
        dataset_train_labels = np.empty((num_dataset_classes, dataset_num_train), dtype=np.int32)
        dataset_train_classes = np.empty((num_dataset_classes, dataset_num_train), dtype=np.int32)

        dataset_test_images = np.empty((num_dataset_classes, dataset_num_test), dtype=np.uint8)
        dataset_test_labels = np.empty((num_dataset_classes, dataset_num_test), dtype=np.int32)
        dataset_test_classes = np.empty((num_dataset_classes, dataset_num_test), dtype=np.int32)

        for i in range(num_dataset_classes):
            arr = np.arange(self.images_per_class)
            np.random.shuffle(arr)

            dataset_train_images[i] = arr[:dataset_num_train]
            dataset_train_labels[i] = np.repeat(i, dataset_num_train)
            dataset_train_classes[i] = np.repeat(self.dataset_classes[i], dataset_num_train)

            dataset_test_images[i] = arr[dataset_num_train:]
            dataset_test_labels[i] = np.repeat(i, dataset_num_test)
            dataset_test_classes[i] = np.repeat(self.dataset_classes[i], dataset_num_test)

        return (dataset_train_images, dataset_train_labels, dataset_train_classes,
                dataset_test_images, dataset_test_labels, dataset_test_classes)

    def build_dataset(self, num_dataset_classes=5, k_shot=5, dataset_num_test=5):
        n, k, d = num_dataset_classes, k_shot, dataset_num_test

        # Build meta training dataset
        self.tr_dataset_train_images, self.tr_dataset_train_labels, \
        self.tr_dataset_train_classes, self.tr_dataset_test_images, \
        self.tr_dataset_test_labels, self.tr_dataset_test_classes = \
        self._build_dataset_helper(self.classes_tr, num_dataset_classes=n, k_shot=k, dataset_num_test=d)

        if len(self.classes_val) > 0:
            # Build meta validation dataset
            self.val_dataset_train_images, self.val_dataset_train_labels, \
            self.val_dataset_train_classes, self.val_dataset_test_images, \
            self.val_dataset_test_labels, self.val_dataset_test_classes = \
            self._build_dataset_helper(self.classes_val, num_dataset_classes=n, k_shot=k, dataset_num_test=d)

        if len(self.classes_ts) > 0:
            # Build meta testing dataset
            self.ts_dataset_train_images, self.ts_dataset_train_labels, \
            self.ts_dataset_train_classes, self.ts_dataset_test_images, \
            self.ts_dataset_test_labels, self.ts_dataset_test_classes = \
            self._build_dataset_helper(self.classes_ts, num_dataset_classes=n, k_shot=k, dataset_num_test=d)

    ##### Get the batches ######################################################
    def _get_train_batch_helper(self, ds_images, ds_labels, ds_classes):
        batch_size = self.k_shot * self.num_dataset_classes
        batch_images = np.zeros((batch_size, self.image_size), dtype=np.uint8)
        batch_labels = np.zeros((batch_size, 1), dtype=np.int32)

        count = 0
        for i in range(self.num_dataset_classes):
            elems = np.random.choice(len(ds_images[i]), self.k_shot, replace=False)
            for j in range(self.k_shot):
                batch_labels[count] = ds_labels[i][elems[j]]
                batch_images[count] = self.dataset.aquire_image(ds_classes[i][elems[j]], elems[j])
                count = count + 1

        batch_labels = np.reshape(batch_labels,(-1,))
        return batch_images, batch_labels

    def _get_test_batch_helper(self, ds_images, ds_labels, ds_classes):
        batch_size = self.dataset_num_test * self.num_dataset_classes
        batch_images = np.zeros((batch_size, self.image_size), dtype=np.uint8)
        batch_labels = np.zeros((batch_size, 1), dtype=np.int32)

        count = 0
        for i in range(self.num_dataset_classes):
            for j in range(self.dataset_num_test):
                batch_labels[count] = ds_labels[i][j]
                batch_images[count] = self.dataset.aquire_image(ds_classes[i][j], j)
                count = count + 1

        batch_labels = np.reshape(batch_labels, (-1,))
        return batch_images, batch_labels

    def _meta_train_get_train_batch(self):
        return self._get_train_batch_helper(self.tr_dataset_train_images,
                                            self.tr_dataset_train_labels,
                                            self.tr_dataset_train_classes)

    def _meta_train_get_test_batch(self):
        return self._get_test_batch_helper(self.tr_dataset_test_images,
                                           self.tr_dataset_test_labels,
                                           self.tr_dataset_test_classes)

    def _meta_val_get_train_batch(self):
        return self._get_train_batch_helper(self.val_dataset_train_images,
                                            self.val_dataset_train_labels,
                                            self.val_dataset_train_classes)

    def _meta_val_get_test_batch(self):
        return self._get_test_batch_helper(self.val_dataset_test_images,
                                           self.val_dataset_test_labels,
                                           self.val_dataset_test_classes)

    def _meta_test_get_train_batch(self):
        return self._get_train_batch_helper(self.ts_dataset_train_images,
                                            self.ts_dataset_train_labels,
                                            self.ts_dataset_train_classes)

    def _meta_test_get_test_batch(self):
        return self._get_test_batch_helper(self.ts_dataset_test_images,
                                           self.ts_dataset_test_labels,
                                           self.ts_dataset_test_classes)

    def get_train_batch(self, meta_type='train'):
        if meta_type == 'train':
            return self._meta_train_get_train_batch()
        elif meta_type == 'val':
            return self._meta_val_get_train_batch()
        elif meta_type == 'test':
            return self._meta_test_get_train_batch()
        else:
            raise ValueError('Cannot parse {}, options are: {}'.format(
                meta_type, ['train', 'val', 'test']))

    def get_test_batch(self, meta_type='train'):
        if meta_type == 'train':
            return self._meta_train_get_test_batch()
        elif meta_type == 'val':
            return self._meta_val_get_test_batch()
        elif meta_type == 'test':
            return self._meta_test_get_test_batch()
        else:
            raise ValueError('Cannot parse: {}. Options are: {}'.format(
                meta_type, ['train', 'val', 'test']))
"""


################################################################################
# Specific class to handle transfer learning problems
class TransferLearnDataManager():
    """TransferLearnDataManager works in a similar way to MetaDataManager but
    instead of creating meta-datasets with the labels being the size of the
    number of classes currently begin trained (eg num_dataset_classes), the size
    of the labels are the size of the entire meta-dataset classes (defined as
    transfer_classes).

    Definitions:
        * Total_classes:
                - The total number of classes in the entire dataset. For example
                  100 classes in Mini-Imagenet.

        * Transfer_train/val/testing_dataset (or t_tvt_dataset):
                - The datasets which contain all of the classes for a specific
                  dataset type.
                - For example 64 classes in the Mini-Imagenet Training dataset.

        * Current_transfer_dataset (or current_meta_dataset):
                - A subset of one of transfer_train/val/testing_datasets.
                - To create: randomly sample classes from one of the tvt_datasets.
                - The total number of classes must be smaller than the total
                  number of classes in EACH of the tvt_datasets.
                - This is also the output size of the learner (optimizee) network.

        * Current_task_dataset (aka current_task or current_problem):
                - Takes a subset of current_transfer_dataset with a small number
                  of classes (usually 2).
                - Used for testing transfer performance of a network and how
                  well the network prevents catastrophic forgetting.
                - Used for split MNIST, split Mini-Imagenet, and other problems.

    How TransferLearnDataManager works (api):
        * Initialization:
                - This creates the class, selects the dataset type and selects
                  current options about the dataset. This also splits the datasets
                  into training, validation, and testing.

        * Select_transfer_batch:
                - This samples from one of the train/val/test datasets and returns
                  the current_transfer dataset to use.
                - This is used as a training example for the meta-optimizer in
                  this paper.
                - Create the labels for each class in the current_task_dataset,
                  this is needed because the labels must stay the same between
                  tasks (unlike meta-learning).

        * Get_current_task:
                - From the current task dataset, sample a small number (usually
                  2) of classes to get the current problem to solve/train on.
                - The shape of the label should be the same as the number of
                  classes in current_transfer_dataset.
                    + This differs from meta-learning, where the shape of the
                      label would be the small number of classes currently being
                      trained (for split MNIST it would be 2).

        * Get train/val/test batch:
                - Get the training batch for the current task (eg 2 classes
                  training examples).
    """

    def __init__(self,
                 dataset=None,
                 num_transfer_classes=None,
                 task_classes=None,
                 data_split_meta=None,
                 data_split_task=None,
                 examples_per_class=None,
                 num_datasets=None):

        if dataset == 'mini-imagenet':
            path = 'datasets/mini-imagenet'
            self.label_type = np.int32
            self.dataset = MiniImagenet(path=path)
        elif dataset == 'simple-linear':
            path = 'datasets/simple_linear_'
            self.label_type = np.float32
            self.dataset = SimpleLinearProblem(path,
                                               shape=10,
                                               examples_per_class=examples_per_class,
                                               weights_mat_shapes=(3, 3),
                                               data_split_meta=data_split_meta,
                                               num_datasets=num_datasets)
        # get information about dataset
        self.meta_train_images = self.dataset.train_images
        self.meta_train_labels = self.dataset.train_labels
        self.meta_val_images = self.dataset.val_images
        self.meta_val_labels = self.dataset.val_labels
        self.meta_test_images = self.dataset.test_images
        self.meta_test_labels = self.dataset.test_labels

        self.task_classes = task_classes
        self.examples_per_class = examples_per_class
        self.input_shape = self.dataset.input_shape
        self.label_shape = self.dataset.label_shape
        self.num_transfer_classes = num_transfer_classes
        self.num_datasets = num_datasets
        self.data_split_task = data_split_task

        self.current_ds = {}

    def build_dataset(self):
        raise NotImplementedError()

    def build_task(self):
        '''Sets up the next task by updating the following vars:
        Updated:
            self.current_train_inputs
            self.current_train_labels
            self.current_test_inputs
            self.current_test_labels
        '''
        # Select task range
        ind1 = self.task_list[self.current_task] * self.task_classes
        ind2 = ind1 + self.task_classes
        if ind2 < len(self.task_list):
            task_indices = np.arange(ind1, ind2)
        else:
            ind2 = ind2 % len(self.task_list)
            task_indices = np.concatenate((np.arange(ind1, len(self.task_list)), np.arange(0, ind2)))

        # Select train/test ranges
        n_train = int(len(self.current_ds_inputs) * self.data_split_task['train'])

        # Select inputs and labels for current task & flatten into 2d (element, dim_of_input/label)
        self.current_train_inputs = self.current_ds_inputs[task_indices, :n_train, :].reshape((-1, self.input_shape))
        self.current_train_labels = self.current_ds_labels[task_indices, :n_train, :].reshape((-1, self.label_shape))
        self.current_test_inputs = self.current_ds_inputs[task_indices, n_train:, :].reshape((-1, self.input_shape))
        self.current_test_labels = self.current_ds_labels[task_indices, n_train:, :].reshape((-1, self.label_shape))

        self.current_task += 1  # self.task_classes # Move to next task

    def get_train_batch(self, batch_size=16):
        '''
        TODO: Figure this out
        NOTE: The way this is done now is very likely to repeat some elements
        between training batches and miss other elements. Should I do this using
        epochs instead? Probably? How important is this? Research this.
        TODO: Fix?
        '''
        if batch_size > self.current_train_inputs.shape[0]:
            raise ValueError('Batch size cannot be greater than the number of elements'
                             + '\nBatch size is:{}'.format(batch_size)
                             + '\nNumber of elements (self.current_train_inputs.shape[0]) is: {}'.format(
                             self.current_train_inputs.shape[0]))

        # Get batch_size random examples (with replacement)
        shuffled_indices = np.arange(self.current_train_inputs.shape[0])
        np.random.shuffle(shuffled_indices)
        shuffled_indices = shuffled_indices[:batch_size]
        return (self.current_train_inputs[shuffled_indices, :],
                self.current_train_labels[shuffled_indices, :])

    def get_test_batch(self, batch_size=16):
        if batch_size > self.current_test_inputs.shape[0]:
            raise ValueError('Batch size cannot be greater than the number of elements'
                             + '\nBatch size is:{}'.format(batch_size)
                             + '\nNumber of elements (self.current_test_inputs.shape[0]) is: {}'.format(
                             self.current_test_inputs.shape[0]))

        # Get batch_size random examples (with replacement)
        shuffled_indices = np.arange(self.current_test_inputs.shape[0])
        np.random.shuffle(shuffled_indices)
        shuffled_indices = shuffled_indices[:batch_size]
        return (self.current_test_inputs[shuffled_indices, :],
                self.current_test_labels[shuffled_indices, :])

    def get_all_test_data(self):
        '''Return the entire set of test data (for use in previous test inputs &
        labels in training script).

        Return:
            inputs: The inputs for the current test set
            labels: The labels for the current test set
        '''
        return (self.current_test_inputs,
                self.current_test_labels)


"""
class MiniImagenetTransferLearnDataManager(TransferLearnDataManager):
    def __init__(self,
                 num_transfer_classes=10,
                 task_classes=1,
                 data_split_meta={'train':0.64, 'val': 0.16, 'test':0.2},
                 data_split_task={'train': 0.7, 'test': 0.3}):
        super(SimpleProbTransferLearnDataManager, self).__init__(
                                    dataset='mini-imagenet',
                                    num_transfer_classes=num_transfer_classes,
                                    task_classes=task_classes,
                                    data_split_meta=data_split_meta,
                                    data_split_task=data_split_task)

    def build_dataset(self, transfer_type):
        '''Build the 'Current_transfer_dataset' with both inputs and labels
        Args: 
            transfer_type: Transfer dataset to use (tranfer train/val/test)
        Updates values of:
            self.current_train_inputs
            self.current_test_inputs
            self.current_train_labels
            self.current_test_labels

        All of these set values are rank 3 tensors. 
            Dim 1 is: The class of the element
            Dim 2 is: The example inside the class
            Dim 3 is: Elements inside the input/label

        For example, to select training example j from class i: 
            self.current_train_inputs[i,j,:] # shape is the dimension of the input
        Or to select training label j from class i:
            self.current_train_labels[i,j,:] # shape is the dimension of the label
        '''
        if transfer_type == 'train':
            images = self.meta_train_images
            ##labels = self.meta_train_labels
        elif transfer_type == 'val':
            images = self.meta_val_images
            ##labels = self.meta_val_labels
        elif transfer_type == 'test':
            images = self.meta_test_images
            ##labels = self.meta_test_labels
        else:
            raise ValueError('{} is an invalid option, Select from train, val,'
                +' or test'.format(transfer_type))

        # Randomly sample classes to use in current transfer dataset
        num_classes = images.shape[0]
        indices = np.arange(num_classes)
        np.random.shuffle(indices)
        indices = indices[:self.num_transfer_classes]

        current_images = images[indices].copy()
        ##current_labels = labels[indices].copy() # Ignored 

        # Get the labels (1s for mini-imagenet)
        ########################################################################
        '''This is a bit cryptic. What the following code does is create the
        labels on the fly for new datasets. It ignores the labels given in 
        mini-imagenet (eg n01930112) and knows that the rows in current_images
        represent different classes.
        '''
        label_scalars = np.ones_like(current_images)

        cl,el,dim = label_scalars.shape
        labels = np.zeros((cl,el,dim*self.num_transfer_classes))
        for i, cl in enumerate(label_scalars):
            ind = i * dim
            labels[i,:,ind:ind+dim] = label_scalars[i,:,:]
        ########################################################################
        self.current_ds_inputs = current_images
        self.current_ds_labels = labels

        self.current_task = 0
        self.task_list = np.arange(num_transfer_classes)
        np.random.shuffle(self.task_list) # Randomize the order of task training
"""


# Does the same thing as TransferLearnDataManager but builds transfer classes
# in order (to make sure we use as much tranfer as possible in the simple
# problem)
class SimpleProbTransferLearnDataManager(TransferLearnDataManager):
    def __init__(self,
                 dataset='simple-linear',
                 num_transfer_classes=27,
                 task_classes=1,
                 data_split_meta={'train': 0.64, 'val': 0.16, 'test': 0.20},
                 data_split_task={'train': 0.7, 'test': 0.3},
                 examples_per_class=1000,
                 num_datasets=100):
        super(SimpleProbTransferLearnDataManager, self).__init__(
            dataset=dataset,
            num_transfer_classes=num_transfer_classes,
            task_classes=task_classes,
            data_split_meta=data_split_meta,
            data_split_task=data_split_task,
            examples_per_class=examples_per_class,
            num_datasets=num_datasets)
        self.built_datasets = 0

    def build_dataset(self, transfer_type):
        '''Build the 'Current_transfer_dataset' with both inputs and labels
        Args:
            transfer_type: Transfer dataset to use (tranfer train/val/test)
        Updates values of:
            self.current_train_inputs
            self.current_test_inputs
            self.current_train_labels
            self.current_test_labels

        All of these set values are rank 3 tensors.
            Dim 1 is: The class of the element
            Dim 2 is: The example inside the class
            Dim 3 is: Elements inside the input/label

        For example, to select training example j from class i:
            self.current_train_inputs[i,j,:] # shape is the dimension of the input
        Or to select training label j from class i:
            self.current_train_labels[i,j,:] # shape is the dimension of the label
        '''
        if transfer_type == 'train':
            images = self.meta_train_images
            labels = self.meta_train_labels
        elif transfer_type == 'val':
            images = self.meta_val_images
            labels = self.meta_val_labels
        elif transfer_type == 'test':
            images = self.meta_test_images
            labels = self.meta_test_labels
        else:
            raise ValueError('{} is an invalid option, Select from train, val, or test'.format(transfer_type))

        # Select classes in order
        bd, ntc = self.built_datasets, self.num_transfer_classes
        indices = np.arange(bd * ntc, (bd + 1) * ntc)
        self.built_datasets += 1

        self.current_ds_inputs = images[indices].copy()
        self.current_ds_labels = labels[indices].copy()

        self.current_task = 0
        self.task_list = np.arange(self.num_transfer_classes)
        print(self.task_list)
        np.random.shuffle(self.task_list)  # Randomize the order of task training

