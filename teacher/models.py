from django.db import models
from django.contrib.postgres.fields import ArrayField

# Create your models here.
import numpy as np


class GenericTeacher:

    def ask(self,
            t=None,
            hist_success=None,
            hist_question=None,
            task_param=None,
            student_param=None,
            student_model=None,
            questions=None,
            replies=None,
            n_iteration=None):

        return \
            self._get_next_node(
                t=t,
                questions=questions,
                replies=replies,
                n_iteration=n_iteration,
                hist_success=hist_success,
                hist_question=hist_question,
                task_param=task_param,
                student_param=student_param,
                student_model=student_model)

    def _get_next_node(self, **kwargs):
        raise NotImplementedError(f"{type(self).__name__} is a meta-class."
                                  "This method need to be overridden")


class Leitner(models.Model, GenericTeacher):

    user_id = models.IntegerField(default=-1)
    delay_factor = models.IntegerField(default=2)
    box_min = models.IntegerField(default=1)
    n_item = models.IntegerField(default=-1)
    taboo = models.IntegerField(default=-1)

    # array of size n_item representing the box
    #             number of i^th item at i^th index.
    box = ArrayField(models.IntegerField(), default=list)

    #  array of size n_item representing the waiting time
    #             of i^th item at i^th index.
    waiting_time = ArrayField(models.IntegerField(), default=list)

    class Meta:

        db_table = 'leitner'
        app_label = 'teacher'

    def modify_sets(self, hist_success, t):
        """
        :param t: time step (integer)
        :param hist_success: list of booleans (True: success, False: failure)
        for every question

        The boxes will be modified according to the following rules:
            * Move an item to the next box for a successful reply by learner
            * Move an item to the previous box for a failure.
        """
        success = hist_success[t-1]
        if success:
            self.box[self.taboo] += 1
        elif self.box[self.taboo] > self.box_min:
            self.box[self.taboo] -= 1

    def update_wait_time(self):
        """
        Update the waiting time of every item in wait_time_arr according to the
         following rules:
            * Taboo will have its wait time changed according to its box.
            * The rest of the item's wait time will be increased by 1
        """

        for i in range(self.n_item):
            if i != self.taboo:
                self.waiting_time[i] += 1
            else:
                self.waiting_time[self.taboo] \
                    = - self.delay_factor**self.box[self.taboo]

    def find_due_items(self):
        """
        :return: arr : array that contains the items that are due to be shown
        Pick all items with positive waiting time.

        Suppose there exist no due item then pick all items except taboo.
        """
        due_items = np.where(np.asarray(self.waiting_time) > 0)[0]
        if len(due_items) == 0:
            complete_arr = np.arange(self.n_item)
            due_items = np.delete(complete_arr, self.taboo)
        return due_items

    @staticmethod
    def find_due_seen_items(due_items, hist_item):
        """
        :param due_items: array that contains items that are due to be shown
        :param hist_item: historic of presented items
        :return: * seen_due_items: as before
                * count: the count of the number of items in seen__due_items

        Finds the items that are seen and are due to be shown.
        """

        # integer array with size of due_items
        #                 * Contains the items that have been seen
        #                     at least once and are due to be shown.
        seen_due_items = np.intersect1d(hist_item, due_items)
        count = len(seen_due_items)

        if count == 0:
            seen_due_items = due_items
            count = len(due_items)
        return seen_due_items, count

    def find_max_waiting(self, items_arr):
        """
        :param items_arr: an integer array that contains the items that should
                be shown.
        :return: arr: contains the items that have been waiting to be shown the
            most.

        Finds those items with maximum waiting time.
        """

        max_wait = float('-inf')
        arr = None
        for i in range(len(items_arr)):
            wait_time_item = self.waiting_time[items_arr[i]]
            if max_wait < wait_time_item:
                arr = [items_arr[i]]
                max_wait = wait_time_item
            elif max_wait == wait_time_item:
                arr.append(items_arr[i])
        return arr

    def pick_least_box(self, max_overdue_items):
        """
        :param max_overdue_items: an integer array that contains the items that
            should be shown.
        :return: items_arr: contains the items that are in the lowest box from
            the max_overdue_items.

        Finds the items present in the lowest box number.
        """

        items_arr = []
        min_box = float('inf')
        for item in max_overdue_items:
            box = self.box[item]
            if box < min_box:
                items_arr = [item]
                min_box = box
            elif box == min_box:
                items_arr.append(item)
        assert len(items_arr), 'This should not be empty'

        return items_arr

    def _get_next_node(self, t,
                       hist_success, hist_question,
                       questions, replies,
                       **kwargs):
        """

        Every item is associated with:
            * A waiting time i.e the time since it was
            last shown to the learner.
                -- maintained in variable wait_time_arr
            * A box that decides the frequency of repeating an item.
                -- maintained in variable learning_progress
        Function implements 4 rules in order:
            1. The items that are due to be shown are picked.
            2. Preference given to the seen items.
            3. Preference given to the items present in lowest box number.
            4. Randomly pick from the said items.

        """
        if t == 0:
            print(self.n_item)
            # Initialize the arrays
            self.box = [0 for _ in range(self.n_item)]
            self.waiting_time = [0 for _ in range(self.n_item)]

            # No past memory, so a random question shown from learning set
            idx_question = np.random.randint(0, self.n_item)

        else:

            self.modify_sets(hist_success=hist_success, t=t)
            self.update_wait_time()

            # Criteria 1, get due items
            due_items = self.find_due_items()

            # preference for seen item
            seen_due_items, count = self.find_due_seen_items(
                due_items=due_items, hist_item=hist_question)

            # items with maximum waiting time
            max_overdue_items = self.find_max_waiting(seen_due_items[:count])

            # pick item in lowest box
            least_box_items = self.pick_least_box(max_overdue_items)

            if len(least_box_items) > 1:
                pick_question_index = np.random.randint(len(least_box_items))
                idx_question = least_box_items[pick_question_index]
            else:
                idx_question = least_box_items[0]

        self.taboo = idx_question
        return idx_question
