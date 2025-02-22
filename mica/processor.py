from collections import deque
from typing import Optional, Dict, Text, List

from mica.agents.agent import Agent
from mica.agents.ensemble_agent import EnsembleAgent
from mica.agents.flow_agent import FlowAgent
from mica.bot import Bot
from mica.event import Event, CurrentAgent, BotUtter, FollowUpAgent, AgentFail, AgentComplete
from mica.tracker import Tracker
from mica.utils import replace_args_in_string, logger


class Processor(object):
    def predict_next_action(self,
                            user_id: Text,
                            tracker: Optional[Tracker] = None,
                            bot: Optional[Bot] = None
                            ) -> List[Event]:
        pass


class DispatcherProcessor(Processor):
    @classmethod
    def create(cls, bot: Optional[Bot] = None):
        return cls()

    def predict_next_action(self,
                            user_id: Text,
                            tracker: Optional[Tracker] = None,
                            bot: Optional[Bot] = None
                            ) -> List[Event]:
        logger.info("Received user message: %s", tracker.latest_message.text)
        meta_agent = bot.entrypoint
        meta_event = CurrentAgent(agent=meta_agent)
        tracker.push_agent(meta_event)

        response = []
        is_end = False
        while not is_end and not tracker.is_agent_stack_empty():
            current_event = tracker.peek_agent()
            logger.debug("[before] Agent stack: %s", list(tracker.agent_stack.keys()))
            current: Agent = current_event.agent
            curr_flow_node = None
            if isinstance(current, FlowAgent):
                curr_flow_node = current_event.metadata
            is_end, response_event_list = current.run(tracker=tracker,
                                                      agents=bot.agents,
                                                      current_nodes=curr_flow_node)
            if isinstance(current, EnsembleAgent):
                tracker.pop_agent()
            for response_event in response_event_list:
                if isinstance(response_event, BotUtter):
                    tracker.update(response_event)
                    text = response_event.text
                    agent_name = current.name
                    text = replace_args_in_string(text, agent_name, tracker)
                    response.append(text)
                if isinstance(response_event, FollowUpAgent):
                    next_agent_name = response_event.next_agent
                    next_agent = bot.agents.get(next_agent_name)
                    tracker.push_agent(CurrentAgent(agent=next_agent))
                if isinstance(response_event, AgentFail) or isinstance(response_event, AgentComplete):
                    tracker.update(response_event)
                    tracker.pop_agent()
                    # call by other agent
                    if current_event.metadata is not None:
                        flow_name = current_event.metadata["flow"]
                        step_id = current_event.metadata["step"]
                        info = tracker.get_or_create_flow_agent(flow_name)
                        info.set_call_result(step_id, response_event)
                        is_end = False
                    elif not is_end and not tracker.is_agent_stack_empty():
                        tracker.push_agent(CurrentAgent(agent=bot.agents.get("exception")))
                if isinstance(response_event, CurrentAgent):
                    tracker.pop_agent()
                    tracker.push_agent(response_event)
            logger.debug("[after] Agent stack: %s", list(tracker.agent_stack.keys()))

        return response


class PriorityProcessor(Processor):
    @classmethod
    def create(cls, bot: Optional[Bot] = None):
        return cls()

    async def predict_next_action(self,
                                  user_id: Text,
                                  tracker: Optional[Tracker] = None,
                                  bot: Optional[Bot] = None
                                  ) -> List[Event]:
        logger.info("Received user message: %s", tracker.latest_message.text)
        response = []
        is_end = False

        if tracker.is_agent_stack_empty():
            # run the entrypoint
            _, response = await bot.entrypoint.run(tracker, agents=bot.agents)

        while not is_end:
            current_event = tracker.peek_agent()
            logger.debug("[before] Agent stack: %s", list(tracker.agent_stack.keys()))
            # no other agents in Agent stack. Stop and ouptut response
            if current_event is None:
                is_end = True
                break
            current: Agent = current_event.agent
            curr_flow_node = None
            if isinstance(current, FlowAgent):
                curr_flow_node = current_event.metadata

            logger.debug("[run] Find agent: %s, now prepare to run this agent.", current)
            is_end, response_event_list = await current.run(tracker=tracker,
                                                            agents=bot.agents,
                                                            tools=bot.tools,
                                                            current_nodes=curr_flow_node)

            for response_event in response_event_list:
                if isinstance(response_event, BotUtter):
                    tracker.update(response_event)
                    text = response_event.text
                    agent_name = current.name
                    text = replace_args_in_string(text, agent_name, tracker)
                    response.append(text)
                if isinstance(response_event, FollowUpAgent):
                    next_agent_name = response_event.next_agent
                    next_agent = bot.agents.get(next_agent_name)
                    tracker.push_agent(CurrentAgent(agent=next_agent))
                if isinstance(response_event, (AgentFail, AgentComplete)):
                    tracker.update(response_event)
                    tracker.pop_agent()
                    # call by other agent
                    if current_event.metadata is not None:
                        flow_name = current_event.metadata["flow"]
                        step_id = current_event.metadata["step"]
                        info = tracker.get_or_create_flow_agent(flow_name)
                        info.set_call_result(step_id, response_event)
                        is_end = False
                if isinstance(response_event, CurrentAgent):
                    tracker.pop_agent()
                    tracker.push_agent(response_event)
            logger.debug("[after] Agent stack: %s", list(tracker.agent_stack.keys()))
        return response