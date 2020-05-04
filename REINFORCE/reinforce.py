import gym
import numpy as np
import random
import matplotlib.pyplot as plt
import math
from collections import deque
import tensorflow as tf
from keras.losses import categorical_crossentropy


if tf.__version__ == "2.1.0":
    import sys
    print("WILL NOT WORK UNTIL TF FIXES CATEGORICAL CROSSENTROPY BUG")
    sys.exit()

class REINFORCE_agent(object):
    def __init__(self, action_size, state_size):
        self.action_space = action_size
        self.state_space = state_size
        self.policy_net = self.make_net()
        self.gamma = 0.99 # DISCOUNT FACTOR, CLOSE TO 1 = LONG TERM
        self.states, self.actions, self.rewards = [], [], []

    def make_net(self):
        x = tf.keras.layers.Input(shape=([self.state_space,]))
        y = tf.keras.layers.Dense(32, activation='relu')(x)
        y = tf.keras.layers.Dense(64, activation='relu')(y)
        y = tf.keras.layers.Dense(32, activation='relu')(y)
        y = tf.keras.layers.Dense(self.action_space, activation='softmax')(y)
        model = tf.keras.models.Model(inputs=x, outputs=y)
        model.summary()
        model.compile(loss=categorical_crossentropy, optimizer=tf.keras.optimizers.Adam())
        return model

    def remember(self, state, action, reward):
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)

    def get_action(self, obs):
        probs = self.policy_net.predict(np.array([obs,]))[0]
        action = np.random.choice(self.action_space, p=probs)
        return action

    def discount_reward(self, rewards):
        d_rewards = np.zeros_like(rewards)
        Gt = 0
        # Discount rewards
        for i in reversed(range(len(rewards))):
            Gt = Gt * self.gamma + rewards[i]
            d_rewards[i] = Gt
        # Normalize
        #d_rewards -= np.mean(d_rewards)
        #d_rewards /= np.std(d_rewards) 
        return d_rewards

    def train(self):
        batch_len = len(self.states)

        rewards = self.discount_reward(self.rewards)


        state = np.zeros(shape=(batch_len, self.state_space))
        action = np.zeros(shape=(batch_len, self.action_space))
        for i in range(batch_len):
            state[i] = self.states[i]
            action[i][self.actions[i]] = rewards[i]

        self.policy_net.fit(state, action, epochs=1, verbose=0)
        self.states.clear()
        self.actions.clear()    
        self.rewards.clear()



# Hyperparameters
ITERATIONS = 1000
windows = 100

env = gym.make("CartPole-v1")
#env.observation_space.shape
print(env.action_space)
print(env.observation_space, env.observation_space.shape[0])
agent = REINFORCE_agent(env.action_space.n, env.observation_space.shape[0])
rewards = []
# Uncomment the line before to load model
#agent.q_network = tf.keras.models.load_model("reinforce_cartpole.h5")
avg_reward = deque(maxlen=ITERATIONS)
best_avg_reward = -math.inf
rs = deque(maxlen=windows)

for i in range(ITERATIONS):
    done = False
    s1 = env.reset()
    total_reward = 0
    while not done:
        #env.render()
        action = agent.get_action(s1)
        s2, reward, done, info = env.step(action)
        total_reward += reward
        agent.remember(s1, action, reward)
        s1 = s2
        
    agent.train()
    rewards.append(total_reward)
    rs.append(total_reward)
    if i >= windows:
        avg = np.mean(rs)
        avg_reward.append(avg)
        if avg > best_avg_reward:
            best_avg_reward = avg
            agent.policy_net.save("reinforce_cartpole.h5")
    else: 
        avg_reward.append(0)
    
    print("\rEpisode {}/{} || Best average reward {}, Current Iteration Reward {}".format(i, ITERATIONS, best_avg_reward, total_reward)) #, end='', flush=True)

np.save("rewards", np.asarray(rewards))
np.save("averages", np.asarray(avg_reward))
plt.ylim(0,500)
plt.plot(rewards, color='olive', label='Reward')
plt.plot(avg_reward, color='red', label='Average')
plt.legend()
plt.ylabel('Reward')
plt.xlabel('Generation')
plt.show()

