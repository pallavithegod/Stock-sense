# -*- coding: utf-8 -*-
"""
NEXUS AI QUANTUM™ - Reinforcement Learning Risk Engine
Advanced RL-based Risk Management and Portfolio Optimization
Copyright © 2025 Future Financial AI. All rights reserved.
"""


import pandas as pd
import numpy as np
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import random
from collections import deque

import logging
logger = logging.getLogger(__name__)

# RL and Optimization Imports
try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    import scipy.optimize as sco
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    OPTIMIZATION_AVAILABLE = False
    logger.warning("Install optimization tools: pip install scipy scikit-learn")

warnings.filterwarnings("ignore")

class QuantumRiskAgent:
    """Reinforcement Learning Agent for Risk Management"""
    
    def __init__(self, 
                 state_size: int = 10, 
                 action_size: int = 3, 
                 learning_rate: float = 0.01,
                 epsilon: float = 1.0,
                 epsilon_decay: float = 0.995,
                 memory_size: int = 2000):
        """
        Initialize RL Risk Agent
        
        Args:
            state_size: Size of state vector (market indicators)
            action_size: Number of actions (BUY, HOLD, SELL)
            learning_rate: Learning rate for Q-learning
            epsilon: Exploration rate
            epsilon_decay: Epsilon decay rate
            memory_size: Experience replay memory size
        """
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.epsilon = epsilon
        self.epsilon_min = 0.01
        self.epsilon_decay = epsilon_decay
        self.memory = deque(maxlen=memory_size)
        
        # Q-table for simple Q-learning (can be replaced with neural network)
        self.q_table = {}
        
        # Performance tracking
        self.total_profit = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.actions_taken = []
        self.rewards_received = []
        
        # Risk parameters
        self.max_position_size = 0.1  # Maximum 10% position size
        self.stop_loss = -0.05  # 5% stop loss
        self.take_profit = 0.15  # 15% take profit
        self.risk_free_rate = 0.05  # 5% risk-free rate
    
    def get_state(self, df: pd.DataFrame, current_idx: int) -> np.ndarray:
        """
        Extract state vector from market data
        
        Args:
            df: Market data DataFrame
            current_idx: Current time index
            
        Returns:
            State vector as numpy array
        """
        try:
            if current_idx < 20:  # Need minimum history
                return np.zeros(self.state_size)
            
            # Extract features for state
            state_features = []
            
            # Price-based features
            current_price = df['Close'].iloc[current_idx]
            price_20_ago = df['Close'].iloc[current_idx - 20]
            price_momentum = (current_price / price_20_ago - 1) * 100
            
            # Volatility
            returns = df['Close'].pct_change().iloc[current_idx-20:current_idx]
            volatility = returns.std() * np.sqrt(252) * 100
            
            # Technical indicators
            if 'RSI' in df.columns:
                rsi = df['RSI'].iloc[current_idx] / 100
            else:
                rsi = 0.5
                
            if 'MACD' in df.columns:
                macd = np.tanh(df['MACD'].iloc[current_idx] / 100)  # Normalize
            else:
                macd = 0
            
            # Volume features
            avg_volume = df['Volume'].iloc[current_idx-20:current_idx].mean()
            current_volume = df['Volume'].iloc[current_idx]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Market regime detection (simplified)
            trend = 1 if price_momentum > 0 else -1
            
            # Build state vector
            state_features = [
                price_momentum / 100,  # Normalize to [-1, 1]
                volatility / 100,      # Normalize
                rsi,
                macd,
                np.tanh(volume_ratio - 1),  # Volume anomaly
                trend,
                current_price / 1000,  # Price level (normalized)
                min(1, max(-1, (current_idx / len(df)) * 2 - 1))  # Time in dataset
            ]
            
            # Pad or trim to exact state size
            while len(state_features) < self.state_size:
                state_features.append(0.0)
            
            return np.array(state_features[:self.state_size])
            
        except Exception as e:
            return np.zeros(self.state_size)
    
    def get_state_key(self, state: np.ndarray) -> str:
        """Convert state to hashable key for Q-table"""
        # Discretize continuous state to create finite state space
        discretized = np.round(state * 10).astype(int)
        return str(discretized.tolist())
    
    def choose_action(self, state: np.ndarray) -> int:
        """
        Choose action using epsilon-greedy policy
        
        Args:
            state: Current state vector
            
        Returns:
            Action index (0=SELL, 1=HOLD, 2=BUY)
        """
        try:
            state_key = self.get_state_key(state)
            
            # Exploration vs exploitation
            if random.random() < self.epsilon:
                return random.randint(0, self.action_size - 1)
            
            # Get Q-values for current state
            if state_key not in self.q_table:
                self.q_table[state_key] = np.random.normal(0, 0.1, self.action_size)
            
            return np.argmax(self.q_table[state_key])
            
        except Exception as e:
            return 1  # Default to HOLD
    
    def calculate_reward(self, 
                        action: int, 
                        price_change: float, 
                        position: float,
                        volatility: float) -> float:
        """
        Calculate reward for taken action
        
        Args:
            action: Action taken (0=SELL, 1=HOLD, 2=BUY)
            price_change: Price change percentage
            position: Current position size
            volatility: Market volatility
            
        Returns:
            Reward value
        """
        try:
            reward = 0.0
            
            # Base reward from price movement and action alignment
            if action == 2:  # BUY
                reward = price_change * 10  # Scale up reward
                # Penalty for buying in high volatility
                reward -= volatility * 2
            elif action == 0:  # SELL
                reward = -price_change * 10  # Profit from price decline
                # Penalty for selling in low volatility (missing upside)
                reward -= max(0, (0.2 - volatility) * 5)
            else:  # HOLD
                reward = -abs(price_change) * 2  # Small penalty for missing moves
                # Bonus for holding in uncertain conditions
                reward += min(2, volatility * 5)
            
            # Risk management rewards
            # Penalty for exceeding position limits
            if abs(position) > self.max_position_size:
                reward -= 10
            
            # Reward for proper risk management
            if action == 0 and position > 0 and price_change < self.stop_loss:
                reward += 5  # Good stop loss execution
            
            if action == 0 and position > 0 and price_change > self.take_profit:
                reward += 10  # Good take profit execution
            
            # Sharpe ratio component
            excess_return = price_change - self.risk_free_rate / 252
            if volatility > 0:
                sharpe_component = excess_return / volatility
                reward += sharpe_component * 2
            
            return reward
            
        except Exception as e:
            return 0.0
    
    def update_q_table(self, 
                      state: np.ndarray, 
                      action: int, 
                      reward: float, 
                      next_state: np.ndarray):
        """
        Update Q-table using Q-learning algorithm
        
        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
        """
        try:
            state_key = self.get_state_key(state)
            next_state_key = self.get_state_key(next_state)
            
            # Initialize Q-values if not exist
            if state_key not in self.q_table:
                self.q_table[state_key] = np.random.normal(0, 0.1, self.action_size)
            if next_state_key not in self.q_table:
                self.q_table[next_state_key] = np.random.normal(0, 0.1, self.action_size)
            
            # Q-learning update rule
            current_q = self.q_table[state_key][action]
            max_next_q = np.max(self.q_table[next_state_key])
            
            # Temporal difference learning
            td_target = reward + 0.95 * max_next_q  # 0.95 is discount factor
            td_error = td_target - current_q
            
            self.q_table[state_key][action] += self.learning_rate * td_error
            
            # Decay exploration rate
            if self.epsilon > self.epsilon_min:
                self.epsilon *= self.epsilon_decay
                
        except Exception as e:
            pass
    
    def train(self, df: pd.DataFrame, episodes: int = 100) -> Dict:
        """
        Train the RL agent on historical data
        
        Args:
            df: Historical market data
            episodes: Number of training episodes
            
        Returns:
            Training results
        """
        try:
            training_results = {
                'total_rewards': [],
                'total_profits': [],
                'win_rates': [],
                'episodes_completed': 0
            }
            
            for episode in range(episodes):
                episode_reward = 0
                episode_profit = 0
                position = 0
                trades_won = 0
                total_episode_trades = 0
                
                # Random start point for robustness
                start_idx = random.randint(50, len(df) - 100)
                end_idx = min(start_idx + random.randint(50, 200), len(df) - 1)
                
                for i in range(start_idx, end_idx - 1):
                    # Get current state
                    state = self.get_state(df, i)
                    
                    # Choose action
                    action = self.choose_action(state)
                    
                    # Calculate price change
                    current_price = df['Close'].iloc[i]
                    next_price = df['Close'].iloc[i + 1]
                    price_change = (next_price / current_price - 1) * 100
                    
                    # Update position based on action
                    if action == 2:  # BUY
                        position = min(self.max_position_size, position + 0.02)
                    elif action == 0:  # SELL
                        position = max(-self.max_position_size, position - 0.02)
                    # HOLD (action == 1) doesn't change position
                    
                    # Calculate volatility for reward
                    returns = df['Close'].pct_change().iloc[max(0, i-20):i]
                    volatility = returns.std() if len(returns) > 1 else 0.02
                    
                    # Calculate reward
                    reward = self.calculate_reward(action, price_change, position, volatility)
                    
                    # Calculate profit
                    trade_profit = position * price_change
                    episode_profit += trade_profit
                    
                    if abs(trade_profit) > 0.1:  # Significant trade
                        total_episode_trades += 1
                        if trade_profit > 0:
                            trades_won += 1
                    
                    # Get next state
                    next_state = self.get_state(df, i + 1)
                    
                    # Update Q-table
                    self.update_q_table(state, action, reward, next_state)
                    
                    episode_reward += reward
                
                # Record episode results
                training_results['total_rewards'].append(episode_reward)
                training_results['total_profits'].append(episode_profit)
                
                win_rate = trades_won / total_episode_trades if total_episode_trades > 0 else 0.5
                training_results['win_rates'].append(win_rate)
                
                training_results['episodes_completed'] = episode + 1
            
            # Calculate final statistics
            avg_reward = np.mean(training_results['total_rewards'])
            avg_profit = np.mean(training_results['total_profits'])
            avg_win_rate = np.mean(training_results['win_rates'])
            
            return {
                'success': True,
                'avg_reward': float(avg_reward),
                'avg_profit': float(avg_profit),
                'avg_win_rate': float(avg_win_rate),
                'final_epsilon': float(self.epsilon),
                'q_table_size': len(self.q_table),
                'training_results': training_results
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_portfolio_recommendation(self, df: pd.DataFrame) -> Dict:
        """
        Get portfolio recommendation based on current market state
        
        Args:
            df: Current market data
            
        Returns:
            Portfolio recommendation dictionary
        """
        try:
            if len(df) < 50:
                return {'error': 'Insufficient data for recommendation'}
            
            # Get current state
            current_state = self.get_state(df, len(df) - 1)
            
            # Get recommended action
            action = self.choose_action(current_state)
            
            # Map action to recommendation
            action_map = {
                0: {'action': 'SELL', 'signal': 'BEARISH', 'position': -0.5},
                1: {'action': 'HOLD', 'signal': 'NEUTRAL', 'position': 0.0},
                2: {'action': 'BUY', 'signal': 'BULLISH', 'position': 0.5}
            }
            
            recommendation = action_map[action]
            
            # Calculate confidence based on Q-value spread
            state_key = self.get_state_key(current_state)
            if state_key in self.q_table:
                q_values = self.q_table[state_key]
                max_q = np.max(q_values)
                min_q = np.min(q_values)
                confidence = (max_q - min_q) / (abs(max_q) + abs(min_q) + 1e-6)
            else:
                confidence = 0.5
            
            # Risk assessment
            recent_volatility = df['Close'].pct_change().tail(20).std() * np.sqrt(252)
            risk_level = 'HIGH' if recent_volatility > 0.3 else 'MEDIUM' if recent_volatility > 0.15 else 'LOW'
            
            return {
                'action': recommendation['action'],
                'signal': recommendation['signal'],
                'recommended_position': recommendation['position'],
                'confidence': float(confidence),
                'risk_level': risk_level,
                'volatility': float(recent_volatility),
                'explanation': f"RL agent recommends {recommendation['action']} based on current market state analysis"
            }
            
        except Exception as e:
            return {'error': f'Recommendation failed: {str(e)}'}

class PortfolioOptimizer:
    """Advanced Portfolio Optimization with Modern Portfolio Theory"""
    
    def __init__(self):
        """Initialize portfolio optimizer"""
        self.returns_data = None
        self.cov_matrix = None
        self.expected_returns = None
        
    def calculate_portfolio_metrics(self, weights: np.ndarray, 
                                  returns: pd.DataFrame) -> Dict:
        """Calculate portfolio metrics for given weights"""
        try:
            # Portfolio return
            portfolio_return = np.sum(returns.mean() * weights) * 252
            
            # Portfolio volatility
            portfolio_var = np.dot(weights.T, np.dot(returns.cov() * 252, weights))
            portfolio_vol = np.sqrt(portfolio_var)
            
            # Sharpe ratio (assuming 5% risk-free rate)
            sharpe_ratio = (portfolio_return - 0.05) / portfolio_vol
            
            return {
                'return': portfolio_return,
                'volatility': portfolio_vol,
                'sharpe_ratio': sharpe_ratio
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def optimize_portfolio(self, returns_df: pd.DataFrame, 
                          target_return: float = None) -> Dict:
        """
        Optimize portfolio using Modern Portfolio Theory
        
        Args:
            returns_df: DataFrame of stock returns
            target_return: Target return (if None, maximize Sharpe ratio)
            
        Returns:
            Optimization results
        """
        try:
            if not OPTIMIZATION_AVAILABLE:
                return {'error': 'Optimization libraries not available'}
            
            n_assets = len(returns_df.columns)
            
            # Calculate expected returns and covariance matrix
            mu = returns_df.mean() * 252
            S = returns_df.cov() * 252
            
            # Constraints: weights sum to 1
            constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
            
            # Bounds: no short selling (0 <= weight <= 1)
            bounds = tuple((0, 1) for _ in range(n_assets))
            
            # Initial guess: equal weights
            x0 = np.array([1/n_assets] * n_assets)
            
            if target_return is None:
                # Maximize Sharpe ratio
                def neg_sharpe(weights):
                    p_return = np.sum(mu * weights)
                    p_vol = np.sqrt(np.dot(weights.T, np.dot(S, weights)))
                    return -(p_return - 0.05) / p_vol
                
                result = sco.minimize(neg_sharpe, x0, method='SLSQP',
                                    bounds=bounds, constraints=constraints)
            else:
                # Minimize risk for target return
                def portfolio_vol(weights):
                    return np.sqrt(np.dot(weights.T, np.dot(S, weights)))
                
                # Additional constraint: target return
                return_constraint = {'type': 'eq', 
                                   'fun': lambda x: np.sum(mu * x) - target_return}
                constraints = [constraints, return_constraint]
                
                result = sco.minimize(portfolio_vol, x0, method='SLSQP',
                                    bounds=bounds, constraints=constraints)
            
            if result.success:
                optimal_weights = result.x
                metrics = self.calculate_portfolio_metrics(optimal_weights, returns_df)
                
                return {
                    'success': True,
                    'weights': optimal_weights.tolist(),
                    'assets': returns_df.columns.tolist(),
                    'expected_return': metrics['return'],
                    'volatility': metrics['volatility'],
                    'sharpe_ratio': metrics['sharpe_ratio']
                }
            else:
                return {'success': False, 'error': 'Optimization failed'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}

class RiskDashboard:
    """Advanced Risk Management Dashboard"""
    
    def __init__(self):
        """Initialize risk dashboard"""
        self.risk_agent = QuantumRiskAgent()
        self.optimizer = PortfolioOptimizer()
    
    def render_rl_training_interface(self, df: pd.DataFrame, symbol: str):
        """Render RL agent training interface"""
        st.markdown("## 🤖 Reinforcement Learning Risk Agent")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🏋️ Agent Training")
            
            episodes = st.slider("Training Episodes", 50, 500, 100)
            learning_rate = st.slider("Learning Rate", 0.001, 0.1, 0.01)
            
            if st.button("🚀 Train RL Agent"):
                with st.spinner("Training reinforcement learning agent..."):
                    self.risk_agent.learning_rate = learning_rate
                    results = self.risk_agent.train(df, episodes=episodes)
                    
                    if results.get('success'):
                        st.success("✅ RL Agent trained successfully!")
                        
                        # Display training metrics
                        col_a, col_b, col_c = st.columns(3)
                        
                        with col_a:
                            st.metric("Avg Reward", f"{results['avg_reward']:.2f}")
                        with col_b:
                            st.metric("Avg Profit", f"{results['avg_profit']:.3f}%")
                        with col_c:
                            st.metric("Win Rate", f"{results['avg_win_rate']:.1%}")
                        
                        # Plot training progress
                        training_data = results['training_results']
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            y=training_data['total_rewards'],
                            mode='lines',
                            name='Episode Rewards',
                            line=dict(color='blue')
                        ))
                        
                        fig.update_layout(
                            title="RL Agent Training Progress",
                            xaxis_title="Episode",
                            yaxis_title="Total Reward",
                            template="plotly_dark"
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    
                    else:
                        logger.error(f"Training failed: {results.get('error')}")
        
        with col2:
            st.markdown("### 📊 Risk Recommendation")
            
            if st.button("🔮 Get RL Recommendation"):
                with st.spinner("Generating RL-based recommendation..."):
                    recommendation = self.risk_agent.get_portfolio_recommendation(df)
                    
                    if 'error' not in recommendation:
                        # Display recommendation
                        action_color = {
                            'BUY': 'green',
                            'SELL': 'red', 
                            'HOLD': 'orange'
                        }
                        
                        color = action_color.get(recommendation['action'], 'blue')
                        
                        st.markdown(f"""
                        <div style="
                            padding: 1rem; 
                            border-radius: 10px; 
                            background: linear-gradient(135deg, {color}22, {color}11);
                            border: 2px solid {color}55;
                            text-align: center;
                        ">
                            <h3 style="color: {color}; margin: 0;">
                                {recommendation['signal']} - {recommendation['action']}
                            </h3>
                            <p style="margin: 0.5rem 0;">
                                Confidence: {recommendation['confidence']:.1%}
                            </p>
                            <p style="margin: 0; font-size: 0.9rem;">
                                Risk Level: {recommendation['risk_level']}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        logger.info(recommendation['explanation'])
                        
                        # Risk metrics
                        st.markdown("**Risk Metrics:**")
                        st.write(f"• Volatility: {recommendation['volatility']:.1%}")
                        st.write(f"• Recommended Position: {recommendation['recommended_position']:.1%}")
                    else:
                        st.error(f"Recommendation failed: {recommendation['error']}")
    
    def render_portfolio_optimization(self, returns_df: pd.DataFrame):
        """Render portfolio optimization interface"""
        st.markdown("## 📈 Modern Portfolio Theory Optimization")
        
        if returns_df is None or len(returns_df.columns) < 2:
            logger.warning("Need at least 2 assets for portfolio optimization")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### ⚙️ Optimization Settings")
            
            opt_type = st.radio(
                "Optimization Type",
                ["Maximize Sharpe Ratio", "Target Return"]
            )
            
            target_return = None
            if opt_type == "Target Return":
                target_return = st.slider(
                    "Target Annual Return", 
                    0.05, 0.50, 0.15, 0.01,
                    format="%.2f"
                )
            
            if st.button("🔍 Optimize Portfolio"):
                with st.spinner("Optimizing portfolio..."):
                    results = self.optimizer.optimize_portfolio(
                        returns_df, 
                        target_return=target_return
                    )
                    
                    if results.get('success'):
                        st.success("✅ Portfolio optimized successfully!")
                        
                        # Display metrics
                        col_a, col_b, col_c = st.columns(3)
                        
                        with col_a:
                            st.metric(
                                "Expected Return", 
                                f"{results['expected_return']:.1%}"
                            )
                        with col_b:
                            st.metric(
                                "Volatility", 
                                f"{results['volatility']:.1%}"
                            )
                        with col_c:
                            st.metric(
                                "Sharpe Ratio", 
                                f"{results['sharpe_ratio']:.2f}"
                            )
                        
                        # Weights visualization
                        weights_df = pd.DataFrame({
                            'Asset': results['assets'],
                            'Weight': results['weights']
                        })
                        
                        fig = px.pie(
                            weights_df, 
                            values='Weight', 
                            names='Asset',
                            title="Optimal Portfolio Allocation"
                        )
                        fig.update_traces(textposition='inside', textinfo='percent+label')
                        fig.update_layout(template="plotly_dark")
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                    else:
                        st.error(f"Optimization failed: {results.get('error')}")
        
        with col2:
            st.markdown("### 📊 Risk Analysis")
            
            # Correlation heatmap
            if len(returns_df.columns) >= 2:
                corr_matrix = returns_df.corr()
                
                fig = px.imshow(
                    corr_matrix,
                    text_auto=True,
                    aspect="auto",
                    title="Asset Correlation Matrix",
                    color_continuous_scale="RdBu"
                )
                fig.update_layout(template="plotly_dark")
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Risk statistics
            st.markdown("**Portfolio Risk Statistics:**")
            
            for asset in returns_df.columns:
                annual_vol = returns_df[asset].std() * np.sqrt(252)
                annual_return = returns_df[asset].mean() * 252
                sharpe = (annual_return - 0.05) / annual_vol if annual_vol > 0 else 0
                
                st.write(f"**{asset}:**")
                st.write(f"  • Return: {annual_return:.1%}")
                st.write(f"  • Volatility: {annual_vol:.1%}")
                st.write(f"  • Sharpe: {sharpe:.2f}")
                st.write("")

# Global instances
risk_dashboard = RiskDashboard()

# Export main classes
__all__ = [
    'QuantumRiskAgent',
    'PortfolioOptimizer', 
    'RiskDashboard',
    'risk_dashboard'
]