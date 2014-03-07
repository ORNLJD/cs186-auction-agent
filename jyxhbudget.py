#!/usr/bin/env python

import sys

from gsp import GSP
from util import argmax_index

class Jyxhbudget:
    """Budget-aware balanced bidding agent"""
    def __init__(self, id, value, budget):
        self.id = id
        self.value = value
        self.budget = budget

    def initial_bid(self, reserve):
        return self.value * 2/3


    def slot_info(self, t, history, reserve):
        """Compute the following for each slot, assuming that everyone else
        keeps their bids constant from the previous rounds.

        Returns list of tuples [(slot_id, min_bid, max_bid)], where
        min_bid is the bid needed to tie the other-agent bid for that slot
        in the last round.  If slot_id = 0, max_bid is 2* min_bid.
        Otherwise, it's the next highest min_bid (so bidding between min_bid
        and max_bid would result in ending up in that slot)
        """
        prev_round = history.round(t-1)
        other_bids = filter(lambda (a_id, b): a_id != self.id, prev_round.bids)

        clicks = prev_round.clicks
        def compute(s):
            (min, max) = GSP.bid_range_for_slot(s, clicks, reserve, other_bids)
            if max == None:
                max = 2 * min
            return (s, min, max)

        info = map(compute, range(len(clicks)))
#        sys.stdout.write("slot info: %s\n" % info)
        return info


    def expected_utils(self, t, history, reserve):
        """
        Project expected utilities for the rest of the rounds given that everyone's bids
        stay constant and we bid for each given slot; takes into account budget constraints.
        """
        # Compute the amount needed per slot
        info = self.slot_info(t, history, reserve)

        # Compute the utility of winning the slot: pay the min_bid because
        # that's the bid of the next highest bid
        clicks = history.round(t-1).clicks

        def calc_util(i):
            (s, min_bid, max_bid) = info[i]

            util = clicks[i] * (self.value - min_bid)
            if self.budget < min_bid * clicks[i] * (48 - t) and min_bid != 0: # Unsustainable
                return util * self.budget / (min_bid * clicks[i] * (48 - t)) 
            else:
                return util

        utilities = map(calc_util, range(len(clicks)))
        return utilities

    def target_slot(self, t, history, reserve):
        """Figure out the best slot to target, assuming that everyone else
        keeps their bids constant from the previous rounds.

        Returns (slot_id, min_bid, max_bid), where min_bid is the bid needed to tie
        the other-agent bid for that slot in the last round.  If slot_id = 0,
        max_bid is min_bid * 2
        """
        i = argmax_index(self.expected_utils(t, history, reserve))

        info = self.slot_info(t, history, reserve)
        return info[i]

    def update_budget(self, t, history):
        agents = history.round(t-1).occupants
        if self.id in agents:
            slot = agents.index(self.id)
            self.budget -= history.round(t-1).slot_payments[slot]

        return self.budget

    def bid(self, t, history, reserve):
        # The Balanced bidding strategy (BB) is the strategy for a player j that, given
        # bids b_{-j},
        # - targets the slot s*_j which maximizes his utility, that is,
        # s*_j = argmax_s {clicks_s (v_j - p_s(j))}.
        # - chooses his bid b' for the next round so as to
        # satisfy the following equation:
        # clicks_{s*_j} (v_j - p_{s*_j}(j)) = clicks_{s*_j-1}(v_j - b')
        # (p_x is the price/click in slot x)
        # If s*_j is the top slot, bid the value v_j

        self.update_budget(t, history)

        prev_round = history.round(t-1)
        (slot, min_bid, max_bid) = self.target_slot(t, history, reserve)

        if self.value < min_bid or slot == 0: # Not expecting to win
            bid = self.value
        else: # Bid regularly
            clicks = prev_round.clicks
            bid = self.value - ((clicks[slot] * (self.value - min_bid)) / clicks[slot-1])

        return bid

    def __repr__(self):
        return "%s(id=%d, value=%d)" % (
            self.__class__.__name__, self.id, self.value)


